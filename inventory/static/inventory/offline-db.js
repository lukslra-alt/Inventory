let db;
let dbReady = false;

const request = indexedDB.open(
    "InventoryPro",
    1
);


request.onupgradeneeded = function(event){

    db = event.target.result;

    db.createObjectStore(
        "products",
        {
            keyPath:"item"
        }
    );
};


request.onsuccess=function(event){

    db = event.target.result;
    dbReady = true;

    // Show whatever is already stored immediately (works offline), then
    // refresh from the network in the background when possible.
    loadOfflineProducts();
    syncProducts();

};


request.onerror = function(event){
    console.error("IndexedDB open failed:", event);
};



function syncProducts(){

    // Database may not be ready yet; skip until it is.
    if (!db) {
        return;
    }

fetch("/offline-products/")
.then(response=>response.json())
.then(products=>{


let transaction =
db.transaction(
"products",
"readwrite"
);


let store =
transaction.objectStore(
"products"
);


store.clear();


products.forEach(product=>{

    store.put(product);

});


if (typeof displayProducts === "function") {
    displayProducts(products);
}


localStorage.setItem(
"lastSync",
new Date().toLocaleString()
);


})
.catch(error=>{
    console.error("Offline products sync failed:", error);
});

}

function loadOfflineProducts() {

    if (!db) {
        return;
    }

    let transaction =
    db.transaction(
        "products",
        "readonly"
    );

    let store =
    transaction.objectStore(
        "products"
    );

    store.getAll().onsuccess =
    function (event) {
        let products = event.target.result;
        if (products && products.length && typeof displayProducts === "function") {
            displayProducts(products);
        }
    };
}

window.addEventListener(
"online",
function(){

    console.log(
    "Internet restored - syncing"
    );

    syncProducts();

});