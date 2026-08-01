document.addEventListener("DOMContentLoaded", function () {
    const search = document.getElementById("searchBox"); // Updated to match your HTML
    const table = document.getElementById("productList"); // Updated to match your HTML

    if (!search || !table) {
        return;
    }

    let timer;
    search.addEventListener("input", function () {
        clearTimeout(timer);

        // Debounce input for 300ms to save server performance
        timer = setTimeout(function () {
            let query = search.value.trim();
            let params = new URLSearchParams();
            params.append("q", query);

            // Retain active category sidebar filters during search
            let urlParams = new URLSearchParams(window.location.search);
            ["category", "subcategory", "level3", "level4"].forEach(function (field) {
                if (urlParams.get(field)) {
                    params.append(field, urlParams.get(field));
                }
            });

            // Use the dynamic window variables set up in the HTML
            const adminFlag = typeof isAdmin !== 'undefined' ? isAdmin : false;
            const costFlag = typeof showCost !== 'undefined' ? showCost : false;

            fetch("/search/?" + params.toString())
                .then(response => response.json())
                .then(data => {
                    // Fallback: If your backend view returns ready-made html content
                    if (data.html) {
                        table.innerHTML = data.html;
                        return;
                    }

                    // Standard: Rebuild the data table dynamically using JSON elements
                    let html = `
                        <div class="table-responsive">
                            <table class="table table-striped table-hover align-middle">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Product</th>
                                        <th>Qty</th>
                                        <th>Price</th>
                                        ${costFlag ? "<th>Cost</th>" : ""}
                                        ${adminFlag ? "<th>Status</th><th>Action</th>" : ""}
                                    </tr>
                                </thead>
                                <tbody>
                    `;

                    if (!data.products || data.products.length === 0) {
                        html = `<div class="alert alert-warning text-center">No products found</div>`;
                    } else {
                        data.products.forEach(product => {
                            html += `
                                <tr>
                                    <td>${product.name}</td>
                                    <td>${product.qty}</td>
                                    <td>${product.price}</td>
                                    ${costFlag ? `<td>${product.avg_cost || '0.00'}</td>` : ""}
                                    ${adminFlag ? `
                                        <td><span class="badge bg-secondary">${product.status}</span></td>
                                        <td><a href="/product/${product.id}/edit/" class="btn btn-sm btn-primary">Edit</a></td>
                                    ` : ""}
                                </tr>
                            `;
                        });
                        html += `</tbody></table></div>`;
                    }
                    table.innerHTML = html;
                })
                .catch(error => {
                    console.error("Search error:", error);
                });
        }, 300);
    });
});
