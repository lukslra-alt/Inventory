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

function statusClass(status) {
    if (status === "NIL") return "bg-danger";
    if (status === "LOW") return "bg-warning text-dark";
    return "bg-success";
}

function buildProductRow(product, showCost, isAdmin) {
    const id = product.id || product.item;
    return `
        <tr>
            <td>${product.name || product.product_name}</td>
            <td class="col-qty">${formatNumber(product.qty)}</td>
            <td class="col-price">${formatNumber(product.price || product.sales_price, 2)}</td>
            ${showCost ? `<td class="col-cost">${formatNumber(product.cost || '0.00', 2)}</td>` : ""}
            ${isAdmin ? `
                <td><span class="badge ${statusClass(product.status)}">${product.status}</span></td>
                <td>
                    <a href="/product/${id}/edit/" class="btn btn-sm btn-primary">Edit</a>
                </td>
            ` : ""}
        </tr>
    `;
}

function renderSearchResults(products, total, hasMore, replace) {
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

    let rows = "";
    products.forEach(product => {
        rows += buildProductRow(product, showCost, isAdmin);
    });

    if (replace) {
        productList.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <small class="text-muted">${total} results</small>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Product</th>
                            <th class="col-qty">Qty</th>
                            <th class="col-price">Price</th>
                            ${showCost ? "<th class=\"col-cost\">Cost</th>" : ""}
                            ${isAdmin ? "<th>Status</th><th>Action</th>" : ""}
                        </tr>
                    </thead>
                    <tbody id="searchBody">
                        ${rows}
                    </tbody>
                </table>
            </div>
            <div id="loadMoreWrap" class="text-center my-3"></div>
        `;
    } else {
        document.getElementById("searchBody").insertAdjacentHTML("beforeend", rows);
    }

    const loadMoreWrap = document.getElementById("loadMoreWrap");
    if (hasMore) {
        loadMoreWrap.innerHTML = `
            <button id="loadMoreBtn" class="btn btn-outline-primary btn-sm">
                Load more (${products.length} of ${total})
            </button>
        `;
    } else {
        loadMoreWrap.innerHTML = "";
    }
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
    fetch("/offline-products/")
        .then(function (response) {
            if (!response.ok) throw new Error("offline products fetch failed");
            return response.json();
        })
        .then(function (products) {
            renderSearchResults(filterOfflineProducts(products || [], query, urlParams), 0, false, true);
        })
        .catch(function () {
            if (!db) {
                return;
            }
            const transaction = db.transaction("products", "readonly");
            const store = transaction.objectStore("products");
            store.getAll().onsuccess = function (event) {
                const products = filterOfflineProducts(event.target.result || [], query, urlParams);
                renderSearchResults(products, 0, false, true);
            };
        });
}

function buildSearchParams(query, urlParams, page) {
    let params = new URLSearchParams();
    params.append("q", query);
    params.append("page", page || 1);
    ["category", "subcategory", "level3", "level4"].forEach(field => {
        if (urlParams.get(field)) {
            params.append(field, urlParams.get(field));
        }
    });
    return params;
}

function fetchSearchPage(params, append, callback) {
    fetch("/search_products/?" + params.toString())
        .then(response => {
            if (!response.ok) throw new Error("Network response error");
            return response.json();
        })
        .then(data => {
            renderSearchResults(data.products, data.total, data.has_more, !append);
            if (callback) callback(data);
        })
        .catch(error => {
            console.error("Search API exception event:", error);
        });
}

document.addEventListener("DOMContentLoaded", function () {
    const searchBox = document.getElementById("searchBox");
    const productList = document.getElementById("productList");
    let debounceTimer = null;
    let currentQuery = "";
    let currentUrlParams = null;

    if (searchBox && productList) {
        searchBox.addEventListener("input", function (e) {
            e.stopPropagation();
            let query = this.value.trim();

            clearTimeout(debounceTimer);

            debounceTimer = setTimeout(() => {
                currentQuery = query;
                currentUrlParams = new URLSearchParams(window.location.search);

                if (!navigator.onLine) {
                    searchOffline(query, currentUrlParams);
                    return;
                }

                const params = buildSearchParams(query, currentUrlParams, 1);
                fetchSearchPage(params, false, function (data) {
                    if (data.has_more) {
                        setupLoadMore(1, data.total);
                    }
                });
            }, 300);
        });
    }

    function setupLoadMore(currentPage, total) {
        const loadMoreWrap = document.getElementById("loadMoreWrap");
        if (!loadMoreWrap) return;

        loadMoreWrap.innerHTML = `
            <button id="loadMoreBtn" class="btn btn-outline-primary btn-sm">
                Load more
            </button>
        `;
        document.getElementById("loadMoreBtn").addEventListener("click", function () {
            const nextPage = currentPage + 1;
            const params = buildSearchParams(currentQuery, currentUrlParams, nextPage);
            this.disabled = true;
            this.textContent = "Loading...";
            fetchSearchPage(params, true, function (data) {
                setupLoadMore(data.page, data.total);
            });
        });
    }

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
