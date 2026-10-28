import fs from "fs";
import path from "path";
const DATA_DIR = path.join(process.cwd(), "data");
export function getAllStockSummaries() { return fs.existsSync(path.join(DATA_DIR, "index.json")) ? JSON.parse(fs.readFileSync(path.join(DATA_DIR, "index.json"), "utf-8")) : []; }
export function getStockFullData(ticker: string) { return fs.existsSync(path.join(DATA_DIR, "stocks", `${ticker}.json`)) ? JSON.parse(fs.readFileSync(path.join(DATA_DIR, "stocks", `${ticker}.json`), "utf-8")) : null; }
export function getAllSectors() { return fs.existsSync(path.join(DATA_DIR, "sectors.json")) ? JSON.parse(fs.readFileSync(path.join(DATA_DIR, "sectors.json"), "utf-8")) : {}; }
