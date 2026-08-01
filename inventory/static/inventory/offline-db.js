let db;

const request = indexedDB.open(
    "InventoryPro",
    1
);


request.onupgradeneeded = function(event){

    db = event.target.result;

    db.createObjectStore(
        "products",
        {
            keyPath:"id"
        }
    );
};


request.onsuccess=function(event){

    db = event.target.result;

    syncProducts();

};



function syncProducts(){

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


displayProducts(products);


localStorage.setItem(
"lastSync",
new Date().toLocaleString()
);


});

}

window.addEventListener(
"online",
function(){

    console.log(
    "Internet restored - syncing"
    );

    syncProducts();

});