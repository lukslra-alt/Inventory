function filterProducts(products) {
    const params = new URLSearchParams(window.location.search);
    const search = (params.get("q") || params.get("search") || "").trim().toLowerCase();
    const category = params.get("category") || "";
    const subcategory = params.get("subcategory") || "";
    const level3 = params.get("level3") || "";
    const level4 = params.get("level4") || "";

    const matchesSearch = (product) => {
        if (!search) return true;
        const fields = [
            product.product_name, product.name, product.category,
            product.subcategory, product.level3, product.level4,
            product.hierarchy_path, product.item
        ];
        return fields.some(field => field && String(field).toLowerCase().includes(search));
    };

    return products.filter(product => {
        if (!matchesSearch(product)) return false;
        if (category && product.category !== category) return false;
        if (subcategory && product.subcategory !== subcategory) return false;
        if (level3 && product.level3 !== level3) return false;
        if (level4 && product.level4 !== level4) return false;
        return true;
    });
}

function formatNumber(value, decimals) {
    if (value === null || value === undefined || value === "") {
        return (decimals === undefined) ? "0" : "0.00";
    }
    const num = Number(value);
    if (isNaN(num)) {
        return String(value);
    }
    if (decimals === undefined) {
        return num.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }
    return num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function displayProducts(products) {
    const productList = document.getElementById("productList");

    if (!productList || !Array.isArray(products)) {
        return;
    }

    products = filterProducts(products);

    if (products.length === 0) {
        productList.innerHTML = `
            <div class="alert alert-warning text-center">
                No products found
            </div>
        `;
        return;
    }

    const isAdmin = window.InventoryState ? window.InventoryState.isAdmin : false;
    const showCost = window.InventoryState ? window.InventoryState.showCost : false;

    let html = `
        <div class="table-responsive">
            <table class="table table-striped table-hover align-middle">
                <thead class="table-dark">
                    <tr>
                        <th>Product</th>
                        <th class="col-qty">Qty</th>
                        <th class="col-price">Price</th>
                        ${showCost ? "<th class=\"col-cost\">Cost</th>" : ""}
                        ${isAdmin ? "<th class=\"col-status\">Status</th><th class=\"col-action\">Action</th>" : ""}
                    </tr>
                </thead>
                <tbody>
    `;

    products.forEach(product => {
        const name = product.product_name || product.name || "";
        html += `
            <tr>
                <td title="${name}">${name}</td>
                <td class="col-qty">${formatNumber(product.qty)}</td>
                <td class="col-price">${formatNumber(product.sales_price || product.price || "0.00", 2)}</td>
                ${showCost ? `<td class="col-cost">${formatNumber(product.cost || "0.00", 2)}</td>` : ""}
                ${isAdmin ? `
                    <td class="col-status"><span class="badge bg-secondary">${product.status || "OK"}</span></td>
                    <td class="col-action">
                        <a href="/product/${product.item || product.id}/edit/" class="btn btn-sm btn-primary">Edit</a>
                    </td>
                ` : ""}
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