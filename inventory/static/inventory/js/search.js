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

            // Execute network payload retrieval only after user activity idles
            debounceTimer = setTimeout(() => {
                let params = new URLSearchParams();
                params.append("q", query);

                let urlParams = new URLSearchParams(window.location.search);
                ["category", "subcategory", "level3", "level4"].forEach(field => {
                    if (urlParams.get(field)) {
                        params.append(field, urlParams.get(field));
                    }
                });

                // Targets the single dedicated JSON processing data API node
                fetch("/search_products/?" + params.toString())
                    .then(response => {
                        if (!response.ok) throw new Error("Network response error");
                        return response.json();
                    })
                    .then(data => {
                        // Access application context config parameters safely
                        const isAdmin = window.InventoryState ? window.InventoryState.isAdmin : false;
                        const showCost = window.InventoryState ? window.InventoryState.showCost : false;

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

                        data.products.forEach(product => {
                            html += `
                                <tr>
                                    <td>${product.name || product.product_name}</td>
                                    <td>${formatNumber(product.qty)}</td>
                                    <td class="col-price">${formatNumber(product.price || product.sales_price, 2)}</td>
                                    ${showCost ? `<td class="col-cost">${formatNumber(product.cost || '0.00', 2)}</td>` : ""}
                                    ${isAdmin ? `
                                        <td><span class="badge bg-secondary">${product.status}</span></td>
                                        <td>
                                            <a href="/product/${product.id}/edit/" class="btn btn-sm btn-primary">Edit</a>
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

                        if (!data.products || data.products.length === 0) {
                            html = `
                                <div class="alert alert-warning text-center">
                                    No products found
                                </div>
                            `;
                        }

                        productList.innerHTML = html;
                    })
                    .catch(error => {
                        console.error("Search API exception event:", error);
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
