const axios = require('axios');
const fs = require('fs');

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function getGoogleSearchResults(query, apiKey, searchEngineId, year) {
    try {
        const startDate = `${year}0101`;
        const endDate = `${year}1231`;

        const response = await axios.get('https://www.googleapis.com/customsearch/v1', {
            params: {
                key: apiKey,
                cx: searchEngineId,
                q: query,
                sort: `date:r:${startDate}:${endDate}`,
                gl: 'VN',
                cr: 'countryVN'
            }
        });

        const totalResults = response.data.searchInformation.totalResults;
        const items = response.data.items || [];

        return {
            totalResults: parseInt(totalResults, 10),
            items: items.map(item => ({
                title: item.title,
                link: item.link,
                snippet: item.snippet
            }))
        };
    } catch (error) {
        console.error('Error fetching Google search results:', error.message);
        throw error;
    }
}

const bank = [
    'Vietcombank', 'Vietinbank', 'BIDV', 'Techcombank', 'VP bank',
    'MB bank', 'Sacombank', 'Á Châu', 'HD bank', 'Agribank',
    'TP bank', 'TMCP Hàng hải Việt Nam', 'Orient Commercial Bank (OCB)',
    'Kienlongbank', 'Nam Á', 'VietcapitalBank', 'Bắc Á', 'SeABank'
];
const keyword = [
    'Smart contracts', 'Decentralized Ledger', 'cryptocurrency',
    'tokenization', 'P2P', 'BaaS',
    'Immutable Records', 'Digital Identity', 'Regulatory Compliance',
    'Cross-Border Payments'
];

async function main() {
    const API_KEY = 'AIza***'; // replace here with google api key
    const SEARCH_ENGINE_ID = '***'; // replace here with google search engine id
    const year = 2023;

    const resultsArray = [];
    const outputFile = 'tes2024search_results.csv';

    fs.writeFileSync(outputFile, 'Bank,Keyword,TotalResults\n', { encoding: 'utf8' });

    for (let i = 10; i < bank.length; i++) {
        for (let j = 0; j < keyword.length; j++) {
            const query = `allintext: ${bank[i]} ${keyword[j]}`;
            try {
                console.log(`Fetching results for: "${query}"`);
                const results = await getGoogleSearchResults(query, API_KEY, SEARCH_ENGINE_ID, year);

                resultsArray.push({
                    bank: bank[i],
                    keyword: keyword[j],
                    totalResults: results.totalResults
                });

                fs.appendFileSync(outputFile, `${bank[i]},${keyword[j]},${results.totalResults}\n`, { encoding: 'utf8' });

                await delay(200);
            } catch (error) {
                console.log(`Error fetching for "${query}": ${error.message}`);
            }
        }
    }


}

main();

