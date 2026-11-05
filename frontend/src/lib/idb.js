// IndexedDB sederhana untuk mode offline (tanpa pustaka tambahan)
// store "cache": salinan data API terakhir (buku, anggota, laporan, pengunjung, ...)
// store "queue": transaksi & pencatatan pengunjung yang menunggu dikirim ke server
// store "rejected": data offline yang ditolak server saat sinkron (bisa dicoba lagi / dihapus)
const DB_NAME = "perpus-offline";
const DB_VERSION = 2;
let dbPromise = null;

function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") { reject(new Error("IndexedDB tidak tersedia")); return; }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("cache")) db.createObjectStore("cache");
      if (!db.objectStoreNames.contains("queue")) db.createObjectStore("queue", { keyPath: "id" });
      if (!db.objectStoreNames.contains("rejected")) db.createObjectStore("rejected", { keyPath: "id" });
    };
    req.onsuccess = () => {
      const db = req.result;
      db.onversionchange = () => { db.close(); dbPromise = null; };
      resolve(db);
    };
    req.onerror = () => reject(req.error);
  });
  dbPromise.catch(() => { dbPromise = null; });
  return dbPromise;
}

function run(store, mode, fn) {
  return openDb().then((db) => new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    const req = fn(tx.objectStore(store));
    tx.oncomplete = () => resolve(req ? req.result : undefined);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  }));
}

export const idbGet = (store, key) => run(store, "readonly", (s) => s.get(key));
export const idbPut = (store, value, key) => run(store, "readwrite", (s) => (key === undefined ? s.put(value) : s.put(value, key)));
export const idbDelete = (store, key) => run(store, "readwrite", (s) => s.delete(key));
export const idbAll = (store) => run(store, "readonly", (s) => s.getAll());
export const idbClear = (store) => run(store, "readwrite", (s) => s.clear());
