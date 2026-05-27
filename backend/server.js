const supplierScraper = require('./supplierScraper');
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const multer = require('multer');
const Tesseract = require('tesseract.js');
const PDFDocument = require('pdfkit');
const { uploadDB, downloadDB } = require('./ftpSync');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());


// Download latest DB from FTP on server start
downloadDB().then(() => {
  console.log('DB sync from FTP complete.');
});

// SQLite DB setup
let db;
try {
  db = new Database('./judith.db');
  console.log('Connected to SQLite database.');
} catch (err) {
  console.error('DB connection error:', err.message);
}

// Create tables if not exist
const createTables = () => {
  db.prepare(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
  )`).run();
  db.prepare(`CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    category TEXT,
    amount REAL,
    description TEXT,
    date TEXT,
    user_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
  )`).run();
  db.prepare(`CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price REAL,
    supplier TEXT,
    sku TEXT
  )`).run();
};
createTables();
// Auth middleware
const authenticate = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.sendStatus(401);
  jwt.verify(token, process.env.JWT_SECRET || 'secret', (err, user) => {
    if (err) return res.sendStatus(403);
    req.user = user;
    next();
  });
};

// CRUD for product price list

app.get('/api/products', authenticate, (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM products').all();
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/products', authenticate, (req, res) => {
  const { name, description, price, supplier, sku } = req.body;
  try {
    const stmt = db.prepare('INSERT INTO products (name, description, price, supplier, sku) VALUES (?, ?, ?, ?, ?)');
    const info = stmt.run(name, description, price, supplier, sku);
    res.json({ id: info.lastInsertRowid });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/products/:id', authenticate, (req, res) => {
  const { name, description, price, supplier, sku } = req.body;
  try {
    const stmt = db.prepare('UPDATE products SET name=?, description=?, price=?, supplier=?, sku=? WHERE id=?');
    const info = stmt.run(name, description, price, supplier, sku, req.params.id);
    res.json({ updated: info.changes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/products/:id', authenticate, (req, res) => {
  try {
    const stmt = db.prepare('DELETE FROM products WHERE id=?');
    const info = stmt.run(req.params.id);
    res.json({ deleted: info.changes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Lookup product price from supplier API (placeholder)
app.get('/api/supplier-price', authenticate, async (req, res) => {
  const { sku, supplier } = req.query;
  // TODO: Integrate with real supplier API here
  // Example: fetch price from supplier API using sku
  // For now, return null to indicate not found
  res.json({ price: null, source: 'supplier', sku, supplier });
});

// Auth routes
app.post('/api/register', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) return res.status(400).json({ error: 'Missing fields' });
  const hash = bcrypt.hashSync(password, 10);
  db.run('INSERT INTO users (username, password) VALUES (?, ?)', [username, hash], function(err) {
    if (err) return res.status(400).json({ error: 'User exists' });
    res.json({ id: this.lastID, username });
  });
});

app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  db.get('SELECT * FROM users WHERE username = ?', [username], (err, user) => {
    if (err || !user) return res.status(400).json({ error: 'Invalid credentials' });
    if (!bcrypt.compareSync(password, user.password)) return res.status(400).json({ error: 'Invalid credentials' });
    const token = jwt.sign({ id: user.id, username: user.username }, process.env.JWT_SECRET || 'secret', { expiresIn: '1d' });
    res.json({ token });
  });
});

// CRUD for transactions (with FTP sync after changes)
app.get('/api/transactions', authenticate, (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM transactions WHERE user_id = ?').all(req.user.id);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/transactions', authenticate, (req, res) => {
  const { type, category, amount, description, date } = req.body;
  try {
    const stmt = db.prepare('INSERT INTO transactions (type, category, amount, description, date, user_id) VALUES (?, ?, ?, ?, ?, ?)');
    const info = stmt.run(type, category, amount, description, date, req.user.id);
    uploadDB();
    res.json({ id: info.lastInsertRowid });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/transactions/:id', authenticate, (req, res) => {
  const { type, category, amount, description, date } = req.body;
  try {
    const stmt = db.prepare('UPDATE transactions SET type=?, category=?, amount=?, description=?, date=? WHERE id=? AND user_id=?');
    const info = stmt.run(type, category, amount, description, date, req.params.id, req.user.id);
    uploadDB();
    res.json({ updated: info.changes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/transactions/:id', authenticate, (req, res) => {
  try {
    const stmt = db.prepare('DELETE FROM transactions WHERE id=? AND user_id=?');
    const info = stmt.run(req.params.id, req.user.id);
    uploadDB();
    res.json({ deleted: info.changes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


// Export transactions (CSV)
app.get('/api/export', authenticate, (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM transactions WHERE user_id = ?').all(req.user.id);
    const csv = ['id,type,category,amount,description,date'].concat(
      rows.map(r => `${r.id},${r.type},${r.category},${r.amount},${r.description},${r.date}`)
    ).join('\n');
    res.header('Content-Type', 'text/csv');
    res.attachment('transactions.csv');
    res.send(csv);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Multer setup for image uploads
const upload = multer({ dest: path.join(__dirname, 'uploads/') });

// Upload receipt image and extract items (OCR)
app.post('/api/receipts', authenticate, upload.single('image'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No image uploaded' });
  try {
    const imagePath = req.file.path;
    const ocrResult = await Tesseract.recognize(imagePath, 'eng');
    // Optionally, parse ocrResult.data.text for items/amounts
    // Save image path and OCR text to DB if needed
    res.json({ text: ocrResult.data.text });
    uploadDB(); // Optionally sync after upload
  } catch (err) {
    res.status(500).json({ error: 'OCR failed' });
  }
});

// Generate PDF invoice
app.post('/api/invoice', authenticate, (req, res) => {
  const { company, client, items, invoiceNumber, date, dueDate } = req.body;
  const doc = new PDFDocument();
  let filename = `invoice_${invoiceNumber || Date.now()}.pdf`;
  res.setHeader('Content-disposition', 'attachment; filename=' + filename);
  res.setHeader('Content-type', 'application/pdf');
  doc.text(`Invoice #${invoiceNumber || ''}`, { align: 'right' });
  doc.text(`Date: ${date || ''}`);
  doc.text(`Due: ${dueDate || ''}`);
  doc.text(`From: ${company || ''}`);
  doc.text(`To: ${client || ''}`);
  doc.moveDown();
  if (Array.isArray(items)) {
    items.forEach(item => {
      doc.text(`${item.name} - ${item.qty} x $${item.price} = $${item.qty * item.price}`);
    });
  }
  doc.end();
  doc.pipe(res);
});


// Search and compare prices from suppliers (must be after app is defined)
app.get('/api/compare-prices', authenticate, async (req, res) => {
  const { query } = req.query;
  if (!query) return res.status(400).json({ error: 'Missing search query' });
  try {
    const [hd, lowes, ace] = await Promise.all([
      supplierScraper.scrapeHomeDepot(query).catch(() => []),
      supplierScraper.scrapeLowes(query).catch(() => []),
      supplierScraper.scrapeAceHardware(query).catch(() => [])
    ]);
    const all = [...hd, ...lowes, ...ace];
    res.json({ results: all });
  } catch (err) {
    res.status(500).json({ error: 'Scraping failed', details: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
