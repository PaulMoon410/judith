/**
 * State snapshot: export/import the SQLite DB as a JSON file served statically
 * by the site. Lets the app bootstrap without an FTP download, and recache
 * the current state whenever data changes.
 *
 * The snapshot is written to ../data/state.json, which is served statically by
 * the Express app (rootDir is the repo root, and data/ is a sibling of backend/).
 */
const path = require('path');
const fs = require('fs');

const ROOT_DIR = path.join(__dirname, '..');
const SNAPSHOT_PATH = path.join(ROOT_DIR, 'data', 'state.json');

function snapshotPath() {
    return process.env.SNAPSHOT_PATH
        ? path.join(ROOT_DIR, process.env.SNAPSHOT_PATH)
        : SNAPSHOT_PATH;
}

/** Export the current DB state to a JSON snapshot. */
function exportSnapshot(db) {
    try {
        const dir = path.dirname(snapshotPath());
        fs.mkdirSync(dir, { recursive: true });

        const users = db.prepare('SELECT id, username FROM users').all();
        const transactions = db.prepare('SELECT * FROM transactions').all();
        const products = db.prepare('SELECT * FROM products').all();

        const snapshot = {
            version: 1,
            exportedAt: new Date().toISOString(),
            users,
            transactions,
            products
        };

        fs.writeFileSync(snapshotPath(), JSON.stringify(snapshot, null, 2), 'utf-8');
        return true;
    } catch (err) {
        console.error('Snapshot export error:', err.message);
        return false;
    }
}

/** Load a JSON snapshot into the DB. Returns true if anything was imported. */
function importSnapshot(db) {
    try {
        const p = snapshotPath();
        if (!fs.existsSync(p)) return false;

        const raw = fs.readFileSync(p, 'utf-8');
        const snap = JSON.parse(raw);
        if (!snap || !Array.isArray(snap.products) && !Array.isArray(snap.transactions)) {
            return false;
        }

        const insertUser = db.prepare('INSERT OR IGNORE INTO users (id, username, password) VALUES (?, ?, ?)');
        const insertTx = db.prepare('INSERT OR IGNORE INTO transactions (id, type, category, amount, description, date, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)');
        const insertProd = db.prepare('INSERT OR IGNORE INTO products (id, name, description, price, supplier, sku) VALUES (?, ?, ?, ?, ?, ?)');

        const txn = db.transaction(() => {
            for (const u of snap.users || []) insertUser.run(u.id, u.username, u.password || '');
            for (const t of snap.transactions || []) insertTx.run(t.id, t.type, t.category, t.amount, t.description, t.date, t.user_id);
            for (const p of snap.products || []) insertProd.run(p.id, p.name, p.description, p.price, p.supplier, p.sku);
        });
        txn();
        return true;
    } catch (err) {
        console.error('Snapshot import error:', err.message);
        return false;
    }
}

/** Count rows in a table; 0 means the DB is empty. */
function tableCount(db, table) {
    try {
        const row = db.prepare(`SELECT COUNT(*) AS c FROM ${table}`).get();
        return row ? row.c : 0;
    } catch (e) {
        return 0;
    }
}

module.exports = { exportSnapshot, importSnapshot, snapshotPath, tableCount };