function displayProducts(products) {

    const productList = document.getElementById("productList");

    if (!productList || !Array.isArray(products)) {
        return;
    }

    if (products.length === 0) {
        productList.innerHTML = `
            <div class="alert alert-warning text-center">
                No products found
            </div>
        `;
        return;
    }

    let html = `
        <div class="table-responsive">
            <table class="table table-striped table-hover align-middle">
                <thead class="table-dark">
                    <tr>
                        <th>Product</th>
                        <th>Price</th>
                    </tr>
                </thead>
                <tbody>
    `;

    products.forEach(product => {
        html += `
            <tr>
                <td>${product.product_name || product.name || ""}</td>
                <td>${product.sales_price || "0.00"}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    productList.innerHTML = html;
}


function loadProducts(){

    // First load from local storage
    loadOfflineProducts();


    // Then update from server
    if(navigator.onLine){

        syncProducts();

    }

}



function loadOfflineProducts(){

    // IndexedDB may not be ready yet (open() is async) or unavailable.
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
    function(event){

        let products =
        event.target.result;


        displayProducts(products);

    };

}

window.addEventListener("load", function(){

    loadProducts();

});