const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_URL = 'https://clinicaltrials.gov/api/v2/studies';
const TARGET_RECORDS = 50000; // Batch limit
const PAGE_SIZE = 100; // Max allowed by ClinicalTrials API typically
const DELAY_MS = 1000; // 1 second delay between requests for rate-limiting

const CHUNK_SIZE = 5000;

// Helper to pause execution
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function ingestBatch() {
    console.log(`Starting ingestion of up to ${TARGET_RECORDS} records...`);
    let allStudies = [];
    let pageToken = null;
    let chunkCount = 1;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    let totalFetched = 0;

    while (totalFetched < TARGET_RECORDS) {
        try {
            console.log(`Fetching ${PAGE_SIZE} records. Current total: ${totalFetched}`);
            const params = { pageSize: PAGE_SIZE };
            if (pageToken) {
                params.pageToken = pageToken;
            }
            
            const response = await axios.get(API_URL, { params });
            const studies = response.data.studies || [];
            allStudies = allStudies.concat(studies);
            totalFetched += studies.length;
            
            pageToken = response.data.nextPageToken;
            
            // Salvataggio chunk per evitare RangeError (memoria massima V8)
            if (allStudies.length >= CHUNK_SIZE) {
                const outputPath = path.join(__dirname, '..', 'staging_area', 'raw', `raw_batch_${timestamp}_part${chunkCount}.json`);
                fs.writeFileSync(outputPath, JSON.stringify({ studies: allStudies }, null, 2));
                console.log(`[CHUNKING] Blocco ${chunkCount} salvato su disco! (${allStudies.length} record scaricati in RAM e svuotati)`);
                allStudies = []; // Svuota la memoria
                chunkCount++;
            }
            
            if (!pageToken || studies.length === 0) {
                console.log("No more pages available.");
                break; // End of data
            }
            
            // Respect rate limiting
            await sleep(DELAY_MS);
            
        } catch (error) {
            console.error("Error fetching data from API:", error.message);
            break;
        }
    }
    
    // Salva il rimanente
    if (allStudies.length > 0) {
        const outputPath = path.join(__dirname, '..', 'staging_area', 'raw', `raw_batch_${timestamp}_part${chunkCount}.json`);
        fs.writeFileSync(outputPath, JSON.stringify({ studies: allStudies }, null, 2));
        console.log(`[CHUNKING] Blocco finale ${chunkCount} salvato su disco!`);
    }
    
    console.log(`Ingestion complete! Total records saved: ${totalFetched}`);
}

ingestBatch();
