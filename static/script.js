document.addEventListener('DOMContentLoaded', function() {
    const processForm = document.getElementById('processForm');
    const convertForm = document.getElementById('convertForm');
    const errorMessage = document.getElementById('errorMessage');
    const convertErrorMessage = document.getElementById('convertErrorMessage');
    const modal = document.getElementById('modal');
    const confirmForm = document.getElementById('confirmForm');

    processForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);

        fetch('/get_product_info', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            document.getElementById('product_name').value = data.product_name;
            document.getElementById('product_sku_base').value = data.product_sku_base;
            document.getElementById('default_price').value = '0'; // Set default price to 0
            document.getElementById('brand').value = ''; // Initialize brand field
            document.getElementById('gender').value = ''; // Initialize gender field
            document.getElementById('suppliers').value = ''; // Initialize suppliers field
            modal.style.display = 'block';
        })
        .catch(error => {
            errorMessage.textContent = error.message || 'An error occurred';
        });
    });

    confirmForm.addEventListener('submit', function(e) {
        e.preventDefault();
        modal.style.display = 'none';
        
        const formData = new FormData(processForm);
        formData.set('product_name', document.getElementById('product_name').value);
        formData.set('product_sku_base', document.getElementById('product_sku_base').value);
        formData.set('default_price', document.getElementById('default_price').value);
        formData.set('brand', document.getElementById('brand').value);
        formData.set('gender', document.getElementById('gender').value);
        formData.set('suppliers', document.getElementById('suppliers').value);
    
        fetch('/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'processed_inventory.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            errorMessage.textContent = error.error || 'An error occurred';
        });
    });

    convertForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);

        fetch('/convert_to_odoo', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'odoo_inventory.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            convertErrorMessage.textContent = error.error || 'An error occurred';
        });
    });

    // Close the modal if the user clicks outside of it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});