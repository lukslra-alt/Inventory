// Safeguard lifecycle orchestration layout
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

function renderSearchResults(products) {
    const productList = document.getElementById("productList");
    const isAdmin = window.InventoryState ? window.InventoryState.isAdmin : false;
    const showCost = window.InventoryState ? window.InventoryState.showCost : false;

    if (!products || products.length === 0) {
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
                        <th>Qty</th>
                        <th class="col-price">Price</th>
                        ${showCost ? "<th class=\"col-cost\">Cost</th>" : ""}
                        ${isAdmin ? "<th>Status</th><th>Action</th>" : ""}
                    </tr>
                </thead>
                <tbody>
    `;

    products.forEach(product => {
        const id = product.id || product.item;
        html += `
            <tr>
                <td>${product.name || product.product_name}</td>
                <td>${formatNumber(product.qty)}</td>
                <td class="col-price">${formatNumber(product.price || product.sales_price, 2)}</td>
                ${showCost ? `<td class="col-cost">${formatNumber(product.cost || '0.00', 2)}</td>` : ""}
                ${isAdmin ? `
                    <td><span class="badge bg-secondary">${product.status}</span></td>
                    <td>
                        <a href="/product/${id}/edit/" class="btn btn-sm btn-primary">Edit</a>
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

function filterOfflineProducts(products, query, urlParams) {
    const q = query.trim().toLowerCase();
    const category = urlParams.get("category") || "";
    const subcategory = urlParams.get("subcategory") || "";
    const level3 = urlParams.get("level3") || "";
    const level4 = urlParams.get("level4") || "";

    return products.filter(product => {
        if (q) {
            const fields = [
                product.product_name, product.name, product.category,
                product.subcategory, product.level3, product.level4,
                product.hierarchy_path, product.item
            ];
            if (!fields.some(field => field && String(field).toLowerCase().includes(q))) {
                return false;
            }
        }
        if (category && product.category !== category) return false;
        if (subcategory && product.subcategory !== subcategory) return false;
        if (level3 && product.level3 !== level3) return false;
        if (level4 && product.level4 !== level4) return false;
        return true;
    });
}

function searchOffline(query, urlParams) {
    if (!db) {
        return;
    }
    const transaction = db.transaction("products", "readonly");
    const store = transaction.objectStore("products");
    store.getAll().onsuccess = function (event) {
        const products = filterOfflineProducts(event.target.result || [], query, urlParams);
        renderSearchResults(products);
    };
}

document.addEventListener("DOMContentLoaded", function () {
    const searchBox = document.getElementById("searchBox");
    const productList = document.getElementById("productList");
    let debounceTimer = null;

    if (searchBox && productList) {
        searchBox.addEventListener("input", function (e) {
            e.stopPropagation();
            let query = this.value.trim();

            // Clear the previous execution window context to throttle calls
            clearTimeout(debounceTimer);

            // Execute payload retrieval only after user activity idles
            debounceTimer = setTimeout(() => {
                let urlParams = new URLSearchParams(window.location.search);
                let params = new URLSearchParams();
                params.append("q", query);
                ["category", "subcategory", "level3", "level4"].forEach(field => {
                    if (urlParams.get(field)) {
                        params.append(field, urlParams.get(field));
                    }
                });

                // When offline, filter the locally synced product data
                if (!navigator.onLine) {
                    searchOffline(query, urlParams);
                    return;
                }

                // Targets the single dedicated JSON processing data API node
                fetch("/search_products/?" + params.toString())
                    .then(response => {
                        if (!response.ok) throw new Error("Network response error");
                        return response.json();
                    })
                    .then(data => {
                        renderSearchResults(data.products);
                    })
                    .catch(error => {
                        console.error("Search API exception event:", error);
                        // Network failed (e.g. lost connection) - fall back to local data
                        searchOffline(query, urlParams);
                    });
            }, 300); // 300 milliseconds delay window execution
        });
    }

    // Programmatic mobile layout toggle safety check
    document.body.addEventListener("click", function (event) {
        if (event.target.classList.contains("category-tree-link")) {
            const offcanvasElement = document.getElementById("mobileCategories");
            if (offcanvasElement && window.bootstrap) {
                const instance = bootstrap.Offcanvas.getInstance(offcanvasElement);
                if (instance) instance.hide();
            }
        }
    });
});
