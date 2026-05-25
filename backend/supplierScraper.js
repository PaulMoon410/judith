const axios = require('axios');
const cheerio = require('cheerio');
const puppeteer = require('puppeteer');

// Example: Scrape Home Depot for a product by search term
async function scrapeHomeDepot(searchTerm) {
  const url = `https://www.homedepot.com/s/${encodeURIComponent(searchTerm)}`;
  const { data } = await axios.get(url);
  const $ = cheerio.load(data);
  const results = [];
  $('.plp-pod').each((i, el) => {
    const name = $(el).find('.product-pod__title').text().trim();
    const price = $(el).find('.price__numbers').text().trim();
    if (name && price) results.push({ name, price, supplier: 'Home Depot' });
  });
  return results;
}

// Example: Scrape Lowes for a product by search term
async function scrapeLowes(searchTerm) {
  const url = `https://www.lowes.com/search?searchTerm=${encodeURIComponent(searchTerm)}`;
  const { data } = await axios.get(url);
  const $ = cheerio.load(data);
  const results = [];
  $('[data-testid="product"]').each((i, el) => {
    const name = $(el).find('[data-testid="product-title"]').text().trim();
    const price = $(el).find('[data-testid="item-price"]').text().trim();
    if (name && price) results.push({ name, price, supplier: 'Lowes' });
  });
  return results;
}

// Example: Scrape Ace Hardware using Puppeteer (for JS-rendered content)
async function scrapeAceHardware(searchTerm) {
  const url = `https://www.acehardware.com/search?query=${encodeURIComponent(searchTerm)}`;
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2' });
  const results = await page.evaluate(() => {
    const items = [];
    document.querySelectorAll('.product-list__item').forEach(el => {
      const name = el.querySelector('.product-list__item__title')?.innerText.trim();
      const price = el.querySelector('.product-list__item__price')?.innerText.trim();
      if (name && price) items.push({ name, price, supplier: 'Ace Hardware' });
    });
    return items;
  });
  await browser.close();
  return results;
}

// Add more suppliers as needed...

module.exports = {
  scrapeHomeDepot,
  scrapeLowes,
  scrapeAceHardware
};
