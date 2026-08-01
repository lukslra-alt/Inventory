function loadProducts(){

    // First load from local storage
    loadOfflineProducts();


    // Then update from server
    if(navigator.onLine){

        syncProducts();

    }

}



function loadOfflineProducts(){

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
    function(event){

        let products =
        event.target.result;


        displayProducts(products);

    };

}

window.addEventListener("load", function(){

    loadProducts();

});