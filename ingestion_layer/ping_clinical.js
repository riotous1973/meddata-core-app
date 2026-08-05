const axios = require('axios');
const fs = require('fs');

async function testSignal() {
    console.log("Inizializzazione ricezione dati da ClinicalTrials.gov...");
    try {
        // Querying a single study using page size 1
        const response = await axios.get('https://clinicaltrials.gov/api/v2/studies', {
            params: {
                pageSize: 1
            }
        });
        
        const data = JSON.stringify(response.data, null, 2);
        
        // Salvataggio nella nostra area di staging di transito
        const outputPath = '../staging_area/raw/raw_test_signal.json';
        fs.writeFileSync(outputPath, data);
        console.log(`Segnale agganciato! Pacchetto dati salvato in ${outputPath}`);
    } catch (error) {
        console.error("Errore di routing:", error.message);
    }
}

testSignal();
