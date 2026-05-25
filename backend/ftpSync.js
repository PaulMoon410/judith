const ftp = require('basic-ftp');
const path = require('path');
const fs = require('fs');

const FTP_CONFIG = {
    host: 'ftp.geocities.ws',
    user: 'Peakecoin',
    password: 'Peake410',
    secure: false
};
const REMOTE_PATH = '/peakecoin/judith/judith.db';
const LOCAL_PATH = path.join(__dirname, '../judith.db');

async function uploadDB() {
    const client = new ftp.Client();
    try {
        await client.access(FTP_CONFIG);
        await client.uploadFrom(LOCAL_PATH, REMOTE_PATH);
        console.log('DB uploaded to FTP.');
    } catch (err) {
        console.error('FTP upload error:', err.message);
    }
    client.close();
}

async function downloadDB() {
    const client = new ftp.Client();
    try {
        await client.access(FTP_CONFIG);
        await client.downloadTo(LOCAL_PATH, REMOTE_PATH);
        console.log('DB downloaded from FTP.');
    } catch (err) {
        console.error('FTP download error:', err.message);
    }
    client.close();
}

module.exports = { uploadDB, downloadDB };