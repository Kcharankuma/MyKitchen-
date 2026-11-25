let cart = [];
let allDishes = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchDishes();
    prefillUserData();
    setupContactForm();

    const cartIcon = document.getElementById('cart-icon');
    const closeCart = document.getElementById('close-cart');
    const checkoutBtn = document.getElementById('checkout-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');

    if (cartIcon) cartIcon.addEventListener('click', toggleCart);
    if (closeCart) closeCart.addEventListener('click', closeCheckoutModal);
    if (checkoutBtn) checkoutBtn.addEventListener('click', handlePlaceOrder);
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeReceiptModal);
});

// --- MENU FETCHING & RENDERING ---
function fetchDishes() {
    fetch('/api/menu')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                allDishes = data.data;
                renderDishes(allDishes);
            }
        })
        .catch(err => console.error("Error loading menu:", err));
}

function renderDishes(dishes) {
    const container = document.getElementById('menu-container');
    if (!container) return;

    if (dishes.length === 0) {
        container.innerHTML = '<p class="empty-msg">No dishes found matching your selection.</p>';
        return;
    }

    container.innerHTML = dishes.map(dish => `
        <div class="food-card">
            <img src="${dish.image}" alt="${dish.title}">
            <div class="food-card-body">
                <h4>${dish.title}</h4>
                <p>${dish.description}</p>
                <div class="food-card-footer">
                    <span>Rs. ${dish.price}</span>
                    <button class="btn-primary" onclick="addToCart(${dish.id}, '${dish.title.replace(/'/g, "\\'")}', ${dish.price})">Add to Cart</button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterMenu(category) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    if (event && event.target) {
        event.target.classList.add('active');
    }

    if (category === 'all') {
        renderDishes(allDishes);
    } else {
        const filtered = allDishes.filter(d => d.category === category);
        renderDishes(filtered);
    }
}

// --- CART STATE MANAGEMENT ---
function toggleCart() {
    const sidebar = document.getElementById('cart-modal-overlay') || document.getElementById('cart-sidebar');
    if (sidebar) {
        const isOpen = sidebar.classList.contains('active') || sidebar.style.display === 'flex';
        if (isOpen) {
            sidebar.classList.remove('open', 'active');
            sidebar.style.display = 'none';
        } else {
            sidebar.classList.add('open', 'active');
            sidebar.style.display = 'flex';
        }
    }
}

function addToCart(id, title, price) {
    const existing = cart.find(i => i.id === id);
    if (existing) {
        existing.qty += 1;
    } else {
        cart.push({ id, title, price, qty: 1 });
    }
    updateCartUI();
}

function changeQty(id, delta) {
    const item = cart.find(i => i.id === id);
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) {
        cart = cart.filter(i => i.id !== id);
    }
    updateCartUI();
}

function updateCartUI() {
    const countEl = document.getElementById('cart-count');
    const itemsEl = document.getElementById('cart-items');
    const subtotalEl = document.getElementById('cart-subtotal') || document.getElementById('bill-subtotal');
    const gstEl = document.getElementById('cart-gst') || document.getElementById('bill-gst');
    const totalEl = document.getElementById('cart-total') || document.getElementById('total-price');

    const totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
    const gst = +(subtotal * 0.05).toFixed(2);
    const grandTotal = +(subtotal + gst).toFixed(2);

    if (countEl) countEl.innerText = totalQty;
    if (subtotalEl) subtotalEl.innerText = `Rs. ${subtotal.toFixed(2)}`;
    if (gstEl) gstEl.innerText = `Rs. ${gst.toFixed(2)}`;
    if (totalEl) totalEl.innerText = `Rs. ${grandTotal.toFixed(2)}`;

    if (itemsEl) {
        if (cart.length === 0) {
            itemsEl.innerHTML = '<p class="empty-msg">Your cart is empty.</p>';
        } else {
            itemsEl.innerHTML = cart.map(i => `
                <div class="bill-line" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span>${i.title} (x${i.qty})</span>
                    <div>
                        <button class="btn-secondary" style="padding: 2px 8px;" onclick="changeQty(${i.id}, -1)">-</button>
                        <span style="margin: 0 6px;">${i.qty}</span>
                        <button class="btn-secondary" style="padding: 2px 8px;" onclick="changeQty(${i.id}, 1)">+</button>
                        <span style="margin-left: 8px; font-weight:600;">Rs. ${(i.price * i.qty).toFixed(2)}</span>
                    </div>
                </div>
            `).join('');
        }
    }
}

// --- LOGGED-IN CUSTOMER PRE-FILL ---
function prefillUserData() {
    fetch('/api/user-data')
        .then(res => res.json())
        .then(data => {
            if (data.logged_in) {
                const nameInput = document.getElementById('cust-name');
                const phoneInput = document.getElementById('cust-phone');
                const emailInput = document.getElementById('cust-email');
                const addrInput = document.getElementById('cust-address');

                if (nameInput) nameInput.value = data.name || '';
                if (phoneInput) phoneInput.value = data.phone || '';
                if (emailInput) emailInput.value = data.email || '';
                if (addrInput) addrInput.value = data.address || '';
            }
        })
        .catch(() => {});
}

// --- CHECKOUT & RECEIPT MODALS ---
function openCheckoutModal() {
    if (cart.length === 0) {
        alert("Your cart is empty!");
        return;
    }
    toggleCart();
    const modal = document.getElementById('checkout-modal');
    if (modal) modal.classList.add('active');
}

function closeCheckoutModal() {
    const modal = document.getElementById('cart-modal-overlay') || document.getElementById('checkout-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.remove('open');
        modal.style.display = 'none';
    }
}

function handlePlaceOrder(e) {
    if (e) e.preventDefault();

    const name = document.getElementById('cust-name')?.value.trim();
    const phone = document.getElementById('cust-phone')?.value.trim();
    const email = document.getElementById('cust-email')?.value.trim() || '';
    const address = document.getElementById('cust-address')?.value.trim();

    if (!name || !phone || !address) {
        alert("Please provide your full delivery details (Name, Phone, and Address).");
        return;
    }

    if (cart.length === 0) {
        alert("Your cart is empty!");
        return;
    }

    const orderData = { name, phone, email, address, cart };

    fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeCheckoutModal();
            cart = [];
            updateCartUI();
            showReceipt(data);
        } else {
            alert(data.message || "Order placement failed.");
        }
    })
    .catch(err => {
        console.error("Order error:", err);
        alert("Could not connect to the server. Please verify your connection.");
    });
}

function showReceipt(data) {
    const receiptModal = document.getElementById('receipt-modal') || document.getElementById('order-modal');
    const orderIdEl = document.getElementById('receipt-order-id') || document.getElementById('receipt-id');
    const nameEl = document.getElementById('receipt-name');
    const phoneEl = document.getElementById('receipt-phone');
    const itemsBody = document.getElementById('receipt-items-body');

    if (orderIdEl) orderIdEl.innerText = data.orderId;
    if (nameEl) nameEl.innerText = data.customerName;
    if (phoneEl) phoneEl.innerText = data.customerPhone;

    if (itemsBody && Array.isArray(data.items)) {
        itemsBody.innerHTML = data.items.map(item => `
            <tr>
                <td>${item.title}</td>
                <td>${item.qty}</td>
                <td>Rs. ${item.price.toFixed(2)}</td>
                <td>Rs. ${(item.price * item.qty).toFixed(2)}</td>
            </tr>
        `).join('');
    }

    const subtotalEl = document.getElementById('receipt-subtotal');
    const grandTotalEl = document.getElementById('receipt-grandtotal');
    if (subtotalEl) subtotalEl.innerText = `Rs. ${data.subtotal.toFixed(2)}`;
    const cgstEl = document.getElementById('receipt-cgst');
    const sgstEl = document.getElementById('receipt-sgst');
    if (cgstEl && data.gst !== undefined) cgstEl.innerText = `Rs. ${(data.gst / 2).toFixed(2)}`;
    if (sgstEl && data.gst !== undefined) sgstEl.innerText = `Rs. ${(data.gst / 2).toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.innerText = `Rs. ${data.grandTotal.toFixed(2)}`;

    if (receiptModal) {
        receiptModal.classList.add('active');
        receiptModal.style.display = 'flex';
    }
}

function closeReceiptModal() {
    const receiptModal = document.getElementById('receipt-modal') || document.getElementById('order-modal');
    if (receiptModal) {
        receiptModal.classList.remove('active');
        receiptModal.style.display = 'none';
    }
}

// --- DYNAMIC "HAVE ANY QUESTIONS? / CONTACT US" SUBMISSION ---
function setupContactForm() {
    const form = document.getElementById('dynamic-contact-form') || document.querySelector('.contact-form form');
    if (form) {
        form.removeEventListener('submit', submitContactForm);
        form.addEventListener('submit', submitContactForm);
    }
}

function submitContactForm(e) {
    e.preventDefault();

    const nameInput = document.getElementById('contact-name');
    const emailInput = document.getElementById('contact-email');
    const phoneInput = document.getElementById('contact-phone');
    const msgInput = document.getElementById('contact-msg') || document.getElementById('contact-message');
    const btn = document.getElementById('contact-btn') || document.querySelector('.contact-button');
    const statusBox = document.getElementById('contact-status-msg');

    const name = nameInput ? nameInput.value.trim() : '';
    const email = emailInput ? emailInput.value.trim() : '';
    const phone = phoneInput ? phoneInput.value.trim() : '';
    const message = msgInput ? msgInput.value.trim() : '';

    if (!name || !email || !phone || !message) {
        displayContactFeedback(statusBox, "Please fill in all contact fields.", false);
        return;
    }

    const originalBtnText = btn ? (btn.value || btn.innerText) : 'Send';
    if (btn) {
        if ('value' in btn) btn.value = 'Sending...';
        else btn.innerText = 'Sending...';
        btn.disabled = true;
    }

    fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, phone, message })
    })
    .then(res => res.json())
    .then(data => {
        resetBtn(btn, originalBtnText);
        if (data.success) {
            displayContactFeedback(statusBox, data.message || `Thank you, ${name}! Your question was submitted successfully.`, true);
            if (nameInput) nameInput.value = '';
            if (emailInput) emailInput.value = '';
            if (phoneInput) phoneInput.value = '';
            if (msgInput) msgInput.value = '';
        } else {
            displayContactFeedback(statusBox, data.message || "Failed to submit message. Please try again.", false);
        }
    })
    .catch(() => {
        resetBtn(btn, originalBtnText);
        displayContactFeedback(statusBox, "Server communication error. Please try again later.", false);
    });
}

function resetBtn(btn, originalText) {
    if (!btn) return;
    btn.disabled = false;
    if ('value' in btn) btn.value = originalText;
    else btn.innerText = originalText;
}

function displayContactFeedback(box, text, isSuccess) {
    if (!box) {
        alert(text);
        return;
    }
    box.style.display = 'block';
    box.style.background = isSuccess ? '#e8f5e9' : '#ffebee';
    box.style.color = isSuccess ? '#2e7d32' : '#c62828';
    box.style.border = isSuccess ? '1px solid #c8e6c9' : '1px solid #ffcdd2';
    box.innerText = text;

    setTimeout(() => {
        box.style.display = 'none';
    }, 5000);
}