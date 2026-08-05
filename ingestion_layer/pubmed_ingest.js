const axios = require('axios');
const fs = require('fs');
const path = require('path');
const xml2js = require('xml2js');

const SEARCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi';
const FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi';

const QUERY = 'clinical trial[Filter]';
const TARGET_RECORDS = 5000; 
const BATCH_SIZE = 200; 
const DELAY_MS = 350; 

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function fetchIds() {
    console.log(`Searching PubMed for: ${QUERY}`);
    const params = {
        db: 'pubmed',
        term: QUERY,
        retmax: TARGET_RECORDS,
        retmode: 'json'
    };
    try {
        const res = await axios.get(SEARCH_URL, { params });
        const ids = res.data.esearchresult.idlist || [];
        console.log(`Found ${ids.length} PubMed IDs.`);
        return ids;
    } catch (e) {
        console.error("Error searching PubMed IDs", e.message);
        return [];
    }
}

async function fetchDetails(ids) {
    console.log(`Fetching details for ${ids.length} articles...`);
    let allArticles = [];
    
    for (let i = 0; i < ids.length; i += BATCH_SIZE) {
        const batchIds = ids.slice(i, i + BATCH_SIZE);
        const params = {
            db: 'pubmed',
            id: batchIds.join(','),
            retmode: 'xml'
        };
        
        try {
            console.log(`Fetching batch ${i} to ${i + batchIds.length}...`);
            const res = await axios.get(FETCH_URL, { params });
            const xmlData = res.data;
            
            const parser = new xml2js.Parser({ explicitArray: false });
            const result = await parser.parseStringPromise(xmlData);
            
            let articles = result.PubmedArticleSet.PubmedArticle || [];
            if (!Array.isArray(articles)) articles = [articles];
            
            allArticles = allArticles.concat(articles);
            
        } catch (e) {
            console.error(`Error fetching batch ${i}:`, e.message);
        }
        
        await sleep(DELAY_MS);
    }
    
    return allArticles;
}

async function ingestPubMed() {
    const ids = await fetchIds();
    if (ids.length === 0) return;
    
    const articles = await fetchDetails(ids);
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outputPath = path.join(__dirname, '..', 'staging_area', 'raw', `pubmed_batch_${timestamp}.json`);
    
    const outputData = {
        source: 'PubMed',
        total_records: articles.length,
        articles: articles
    };
    
    fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2));
    console.log(`PubMed Ingestion complete! ${articles.length} records saved to ${outputPath}`);
}

ingestPubMed();
