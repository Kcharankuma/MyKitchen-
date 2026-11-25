let cart = [];
let allMenuItems = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchUserData();
    fetchMenuItems();
    setupCartEvents();
    setupSearchAndFilter();
});

function fetchUserData() {
    fetch('/api/user-data')
        .then(res => res.json())
        .then(data => {
            if (data.logged_in) {
                if (document.getElementById('cust-name')) document.getElementById('cust-name').value = data.name || '';
                if (document.getElementById('cust-phone')) document.getElementById('cust-phone').value = data.phone || '';
                if (document.getElementById('cust-address')) document.getElementById('cust-address').value = data.address || '';
            }
        });
}

function fetchMenuItems() {
    fetch('/api/menu')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                allMenuItems = data.data;
                renderMenuItems(allMenuItems);
            }
        });
}

function renderMenuItems(items) {
    const container = document.getElementById('menu-container');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = `<p class="empty-msg">No dishes found.</p>`;
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="menu-box">
            <div class="menu-img">
                <img src="${item.image}" alt="${item.title}">
            </div>
            <div class="text">
                <h3>${item.title}</h3>
                <p>${item.description}</p>
                <div class="price-btn">
                    <span class="price">₹${item.price}</span>
                    <button class="add-to-cart-btn" onclick="addToCart(${item.id}, '${item.title.replace(/'/g, "\\'")}', ${item.price})">Add to Cart</button>
                </div>
            </div>
        </div>
    `).join('');
}

// Add item without opening side drawer automatically
// Add item to cart and trigger notification message
function addToCart(id, title, price) {
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.qty += 1;
    } else {
        cart.push({ id, title, price, qty: 1 });
    }
    updateCartUI();
    showToast(`"${title}" added to cart!`);
}

// Function to display notification message
function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<i class='bx bx-check-circle'></i> ${message}`;

    container.appendChild(toast);

    // Automatically remove toast after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function updateCartUI() {
    const cartCount = document.getElementById('cart-count');
    const cartItemsContainer = document.getElementById('cart-items');
    const subtotalEl = document.getElementById('bill-subtotal');
    const gstEl = document.getElementById('bill-gst');
    const totalEl = document.getElementById('total-price');

    const totalQty = cart.reduce((acc, item) => acc + item.qty, 0);
    if (cartCount) cartCount.innerText = totalQty;

    if (cart.length === 0) {
        if (cartItemsContainer) cartItemsContainer.innerHTML = `<p class="empty-msg">Your cart is empty.</p>`;
        if (subtotalEl) subtotalEl.innerText = '₹0.00';
        if (gstEl) gstEl.innerText = '₹0.00';
        if (totalEl) totalEl.innerText = '₹0.00';
        return;
    }

    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);
    const gst = subtotal * 0.05;
    const grandTotal = subtotal + gst;

    if (cartItemsContainer) {
        cartItemsContainer.innerHTML = cart.map(item => `
            <div class="cart-item">
                <div class="cart-item-info">
                    <h4>${item.title}</h4>
                    <p>₹${item.price} x ${item.qty} = ₹${item.price * item.qty}</p>
                </div>
                <div class="cart-item-controls">
                    <button onclick="changeQty(${item.id}, -1)">-</button>
                    <span>${item.qty}</span>
                    <button onclick="changeQty(${item.id}, 1)">+</button>
                </div>
            </div>
        `).join('');
    }

    if (subtotalEl) subtotalEl.innerText = `₹${subtotal.toFixed(2)}`;
    if (gstEl) gstEl.innerText = `₹${gst.toFixed(2)}`;
    if (totalEl) totalEl.innerText = `₹${grandTotal.toFixed(2)}`;
}

function changeQty(id, delta) {
    const item = cart.find(i => i.id === id);
    if (item) {
        item.qty += delta;
        if (item.qty <= 0) {
            cart = cart.filter(i => i.id !== id);
        }
    }
    updateCartUI();
}

function setupCartEvents() {
    const cartIcon = document.getElementById('cart-icon');
    const closeCart = document.getElementById('close-cart');
    const checkoutBtn = document.getElementById('checkout-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');

    if (cartIcon) cartIcon.addEventListener('click', openCart);
    if (closeCart) closeCart.addEventListener('click', closeCartDrawer);

    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', () => {
            const name = document.getElementById('cust-name').value.trim();
            const phone = document.getElementById('cust-phone').value.trim();
            const address = document.getElementById('cust-address').value.trim();

            if (cart.length === 0) {
                alert('Your cart is empty!');
                return;
            }
            if (!name || !phone || !address) {
                return;
                return;
            }

            fetch('/api/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart, name, phone, address })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showReceiptModal(data);
                    cart = [];
                    updateCartUI();
                    closeCartDrawer();
                } else {
                    alert(data.message || 'Error placing order');
                }
            });
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            document.getElementById('order-modal').classList.remove('active');
        });
    }
}

// Opens Cart as Modal Overlay when clicking red count icon
function openCart() {
    document.getElementById('cart-modal-overlay').classList.add('active');
}

function closeCartDrawer() {
    document.getElementById('cart-modal-overlay').classList.remove('active');
}

function showReceiptModal(data) {
    document.getElementById('receipt-id').innerText = `#${data.orderId}`;
    document.getElementById('receipt-name').innerText = data.customerName;
    document.getElementById('receipt-phone').innerText = data.customerPhone;

    const itemsTbody = document.getElementById('receipt-items-body');
    itemsTbody.innerHTML = data.items.map(item => `
        <tr>
            <td>${item.title}</td>
            <td>${item.qty}</td>
            <td>₹${item.price}</td>
            <td>₹${(item.price * item.qty).toFixed(2)}</td>
        </tr>
    `).join('');

    const subtotal = data.subtotal;
    const halfGst = (data.gst / 2);

    document.getElementById('receipt-subtotal').innerText = `₹${subtotal.toFixed(2)}`;
    document.getElementById('receipt-cgst').innerText = `₹${halfGst.toFixed(2)}`;
    document.getElementById('receipt-sgst').innerText = `₹${halfGst.toFixed(2)}`;
    document.getElementById('receipt-grandtotal').innerText = `₹${data.grandTotal.toFixed(2)}`;

    document.getElementById('order-modal').classList.add('active');
}

function setupSearchAndFilter() {
    const searchInput = document.getElementById('food-search');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const sortSelect = document.getElementById('price-sort');

    if (searchInput) searchInput.addEventListener('input', applyFilters);

    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            applyFilters();
        });
    });

    if (sortSelect) sortSelect.addEventListener('change', applyFilters);
}

function applyFilters() {
    let filtered = [...allMenuItems];
    const searchTerm = document.getElementById('food-search').value.toLowerCase().trim();
    const activeCategory = document.querySelector('.filter-btn.active').dataset.filter;
    const sortVal = document.getElementById('price-sort').value;

    if (searchTerm) filtered = filtered.filter(item => item.title.toLowerCase().includes(searchTerm));
    if (activeCategory !== 'all') filtered = filtered.filter(item => item.category === activeCategory);

    if (sortVal === 'low-to-high') filtered.sort((a, b) => a.price - b.price);
    else if (sortVal === 'high-to-low') filtered.sort((a, b) => b.price - a.price);

    renderMenuItems(filtered);
}

// --- AUTO-WIRE CART & CHECKOUT MODAL HANDLERS ---
document.addEventListener('DOMContentLoaded', () => {
    const cartIcon = document.getElementById('cart-icon');
    const closeCart = document.getElementById('close-cart');
    const cartOverlay = document.getElementById('cart-modal-overlay');
    const checkoutBtn = document.getElementById('checkout-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');

    if (cartIcon && cartOverlay) {
        cartIcon.onclick = () => {
            cartOverlay.classList.add('active', 'open');
            cartOverlay.style.display = 'flex';
        };
    }
    if (closeCart && cartOverlay) {
        closeCart.onclick = () => {
            cartOverlay.classList.remove('active', 'open');
            cartOverlay.style.display = 'none';
        };
    }
    if (closeModalBtn) {
        closeModalBtn.onclick = () => {
            const orderModal = document.getElementById('order-modal');
            if (orderModal) {
                orderModal.classList.remove('active');
                orderModal.style.display = 'none';
            }
        };
    }
    if (checkoutBtn) {
        checkoutBtn.onclick = async (e) => {
            e.preventDefault();
            const name = document.getElementById('cust-name')?.value.trim();
            const phone = document.getElementById('cust-phone')?.value.trim();
            const email = document.getElementById('cust-email')?.value.trim() || '';
            const address = document.getElementById('cust-address')?.value.trim();

            if (!name || !phone || !address) {
                alert('Please provide your full delivery details (Name, Phone, and Address).');
                return;
            }
            if (typeof cart === 'undefined' || !cart.length) {
                alert('Your cart is empty!');
                return;
            }

            checkoutBtn.disabled = true;
            checkoutBtn.innerText = 'Processing...';
            try {
                const res = await fetch('/api/order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, phone, email, address, cart })
                });
                const data = await res.json();
                if (data.success) {
                    if (cartOverlay) {
                        cartOverlay.classList.remove('active', 'open');
                        cartOverlay.style.display = 'none';
                    }
                    cart = [];
                    if (typeof updateCartUI === 'function') updateCartUI();

                    const orderModal = document.getElementById('order-modal');
                    if (document.getElementById('receipt-id')) document.getElementById('receipt-id').innerText = '#' + data.orderId;
                    if (document.getElementById('receipt-name')) document.getElementById('receipt-name').innerText = data.customerName;
                    if (document.getElementById('receipt-phone')) document.getElementById('receipt-phone').innerText = data.customerPhone;
                    if (document.getElementById('receipt-subtotal')) document.getElementById('receipt-subtotal').innerText = '₹' + data.subtotal.toFixed(2);
                    if (document.getElementById('receipt-cgst')) document.getElementById('receipt-cgst').innerText = '₹' + (data.gst / 2).toFixed(2);
                    if (document.getElementById('receipt-sgst')) document.getElementById('receipt-sgst').innerText = '₹' + (data.gst / 2).toFixed(2);
                    if (document.getElementById('receipt-grandtotal')) document.getElementById('receipt-grandtotal').innerText = '₹' + data.grandTotal.toFixed(2);
                    if (document.getElementById('receipt-items-body') && Array.isArray(data.items)) {
                        document.getElementById('receipt-items-body').innerHTML = data.items.map(i =>
                            `<tr><td>${i.title}</td><td>${i.qty}</td><td>₹${i.price.toFixed(2)}</td><td>₹${(i.price * i.qty).toFixed(2)}</td></tr>`
                        ).join('');
                    }
                    if (orderModal) {
                        orderModal.classList.add('active');
                        orderModal.style.display = 'flex';
                    }
                } else {
                    alert(data.message || 'Order placement failed.');
                }
            } catch (err) {
                alert('Error placing order. Please try again.');
            } finally {
                checkoutBtn.disabled = false;
                checkoutBtn.innerText = 'Pay & Place Order';
            }
        };
    }
});


// --- AUTO-FILL LOGGED-IN CUSTOMER DELIVERY DETAILS ---
async function fillLoggedInCustomerDetails() {
    try {
        const res = await fetch('/api/user-data');
        const data = await res.json();
        if (data.logged_in) {
            const nameEl = document.getElementById('cust-name');
            const phoneEl = document.getElementById('cust-phone');
            const emailEl = document.getElementById('cust-email');
            const addrEl = document.getElementById('cust-address');

            if (nameEl && data.name) nameEl.value = data.name;
            if (phoneEl && data.phone) phoneEl.value = data.phone;
            if (emailEl && data.email) emailEl.value = data.email;
            if (addrEl && data.address) addrEl.value = data.address;
        }
    } catch (e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    fillLoggedInCustomerDetails();
    const cartIconBtn = document.getElementById('cart-icon');
    if (cartIconBtn) {
        cartIconBtn.addEventListener('click', fillLoggedInCustomerDetails);
    }
});


// --- UNIFIED CONTACT US HANDLER (EMAILS CUSTOMER + ADMIN) ---
document.addEventListener('DOMContentLoaded', () => {
    const contactSection = document.getElementById('contact') || document.querySelector('.contact, .contact-form');
    if (!contactSection) return;

    // Clone form/button to strip any leftover duplicate event listeners
    const oldForm = contactSection.querySelector('form');
    const targetContainer = oldForm || contactSection;

    const handleContactSubmit = async (e) => {
        if (e) e.preventDefault();

        const textInputs = Array.from(targetContainer.querySelectorAll('input:not([type="submit"]):not([type="button"])'));
        const textarea = targetContainer.querySelector('textarea');

        const name = (document.getElementById('contact-name')?.value || textInputs[0]?.value || '').trim();
        const email = (document.getElementById('contact-email')?.value || textInputs[1]?.value || '').trim();
        const message = (document.getElementById('contact-msg')?.value || document.getElementById('contact-message')?.value || textarea?.value || '').trim();

        if (!name || !email || !message) {
            alert('Please fill in your Name, Email, and Message.');
            return;
        }

        const btn = targetContainer.querySelector('button, input[type="submit"], .contact-button, .btn');
        const origText = btn ? (btn.value || btn.innerText) : 'Send';
        if (btn) {
            btn.disabled = true;
            if ('value' in btn) btn.value = 'Sending...';
            else btn.innerText = 'Sending...';
        }

        try {
            const res = await fetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, message })
            });
            const data = await res.json();
            alert(data.message || 'Thank you! Your message has been sent to us and a copy was emailed to you.');
            if (data.success) {
                textInputs.forEach(i => i.value = '');
                if (textarea) textarea.value = '';
            }
        } catch (err) {
            alert('Network error while sending message. Please try again.');
        } finally {
            if (btn) {
                btn.disabled = false;
                if ('value' in btn) btn.value = origText;
                else btn.innerText = origText;
            }
        }
    };

    if (oldForm) {
        const freshForm = oldForm.cloneNode(true);
        oldForm.parentNode.replaceChild(freshForm, oldForm);
        freshForm.addEventListener('submit', handleContactSubmit);
    } else {
        const btn = targetContainer.querySelector('button, input[type="submit"], .contact-button, .btn');
        if (btn) {
            const freshBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(freshBtn, btn);
            freshBtn.addEventListener('click', handleContactSubmit);
        }
    }
});
