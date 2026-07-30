document.addEventListener(
    "DOMContentLoaded",
    function () {

        const search =
            document.getElementById(
                "product-search"
            );

        const table =
            document.getElementById(
                "product-table"
            );


        if (!search) {
            return;
        }


        let timer;


        search.addEventListener(
            "input",
            function () {

                clearTimeout(timer);


                timer = setTimeout(
                    function () {

                        fetch(
                            `/search/?q=${encodeURIComponent(search.value)}`
                        )

                        .then(
                            response =>
                            response.json()
                        )

                        .then(
                            data => {

                                table.innerHTML =
                                    data.html;

                            }
                        );


                    },
                    300
                );

            }
        );


    }
);