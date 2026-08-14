let productSort = { field: "product_name", dir: "asc" };
let productStockFilter = "all";

function statusClass(status) {
    if (status === "NIL") return "bg-danger";
    if (status === "LOW") return "bg-warning text-dark";
    return "bg-success";
}

function statusWeight(status) {
    if (status === "NIL") return 0;
    if (status === "LOW") return 1;
    return 2; // OK
}

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

function filterStock(products) {
    if (productStockFilter === "all") return products;
    return products.filter(product => {
        if (productStockFilter === "low") return product.status === "LOW";
        if (productStockFilter === "nil") return product.status === "NIL";
        return true;
    });
}

function sortProducts(products) {
    const { field, dir } = productSort;
    const factor = dir === "desc" ? -1 : 1;
    return products.slice().sort((a, b) => {
        if (field === "product_name") {
            const av = (a.product_name || a.name || "").toLowerCase();
            const bv = (b.product_name || b.name || "").toLowerCase();
            return av < bv ? -1 * factor : av > bv ? 1 * factor : 0;
        }
        if (field === "qty") {
            return ((Number(a.qty) || 0) - (Number(b.qty) || 0)) * factor;
        }
        if (field === "status") {
            return (statusWeight(a.status) - statusWeight(b.status)) * factor;
        }
        return 0;
    });
}

function sortIndicator(field) {
    if (productSort.field !== field) return "";
    return productSort.dir === "asc" ? " ▲" : " ▼";
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

    // Keep the raw list so sorting/filtering can re-render without refetching.
    window.lastProductList = products;

    products = sortProducts(filterStock(filterProducts(products)));

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
                        <th class="sortable" data-sort="product_name">Product${sortIndicator("product_name")}</th>
                        <th class="col-qty sortable" data-sort="qty">Qty${sortIndicator("qty")}</th>
                        <th class="col-price">Price</th>
                        ${showCost ? `<th class="col-cost">Cost</th>` : ""}
                        ${isAdmin ? `<th class="col-status sortable" data-sort="status">Status${sortIndicator("status")}</th><th class="col-action">Action</th>` : ""}
                    </tr>
                </thead>
                <tbody>
    `;

    products.forEach(product => {
        const name = product.product_name || product.name || "";
        const statusCls = statusClass(product.status);
        html += `
            <tr>
                <td title="${name}">${name}</td>
                <td class="col-qty">${formatNumber(product.qty)}</td>
                <td class="col-price">${formatNumber(product.sales_price || product.price || "0.00", 2)}</td>
                ${showCost ? `<td class="col-cost">${formatNumber(product.cost || "0.00", 2)}</td>` : ""}
                ${isAdmin ? `
                    <td class="col-status"><span class="badge ${statusCls}">${product.status || "OK"}</span></td>
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

function onSortHeaderClick(event) {
    const th = event.target.closest("th.sortable");
    if (!th) return;
    const field = th.getAttribute("data-sort");
    if (productSort.field === field) {
        productSort.dir = productSort.dir === "asc" ? "desc" : "asc";
    } else {
        productSort.field = field;
        productSort.dir = "asc";
    }
    if (window.lastProductList) displayProducts(window.lastProductList);
}

function setStockFilter(value) {
    productStockFilter = value;
    document.querySelectorAll(".stock-filter-btn").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-stock") === value);
    });
    if (window.lastProductList) displayProducts(window.lastProductList);
}

function loadProducts() {
    loadOfflineProducts();
    if (navigator.onLine) {
        syncProducts();
    }
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
        displayProducts(products);
    };
}

const productListEl = document.getElementById("productList");
if (productListEl) {
    productListEl.addEventListener("click", onSortHeaderClick);
}

window.addEventListener("load", function () {
    loadProducts();
});
