document.addEventListener('DOMContentLoaded', () => {
    // 1. Flash Message Auto-Dismiss
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        }, 5000);

        // Click to dismiss
        msg.addEventListener('click', () => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        });
    });

    // 2. Navbar Mobile Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // 3. Countdown Timer (Checkout Page)
    const countdownEl = document.getElementById('checkout-countdown');
    if (countdownEl) {
        const remainingStr = countdownEl.getAttribute('data-remaining-seconds');
        const cancelUrl = countdownEl.getAttribute('data-cancel-url');
        const minEl = document.getElementById('countdown-minutes');
        const secEl = document.getElementById('countdown-seconds');
        const progressEl = countdownEl.querySelector('.countdown-progress');
        
        const remainingSeconds = parseFloat(remainingStr);
        const expiresAt = new Date().getTime() + (remainingSeconds * 1000);
        const totalDuration = 5 * 60 * 1000; // 5 minutes in ms
        
        const updateTimer = () => {
            const now = new Date().getTime();
            const distance = expiresAt - now;

            if (distance < 0) {
                clearInterval(timerInterval);
                minEl.textContent = "00";
                secEl.textContent = "00";
                if (progressEl) progressEl.style.width = "0%";
                
                // Expired! Cancel the lock.
                fetch(cancelUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                }).then(() => {
                    alert('Time expired! Your seats have been released.');
                    window.location.href = '/events';
                }).catch(err => {
                    console.error('Error cancelling:', err);
                    window.location.href = '/events';
                });
                return;
            }

            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            minEl.textContent = minutes.toString().padStart(2, '0');
            secEl.textContent = seconds.toString().padStart(2, '0');

            if (progressEl) {
                const percentage = Math.max(0, (distance / totalDuration) * 100);
                progressEl.style.width = `${percentage}%`;
            }

            if (distance < 60000) { // less than 1 minute
                countdownEl.classList.add('countdown-warning');
            }
        };

        updateTimer();
        const timerInterval = setInterval(updateTimer, 1000);
    }

    // 4. Quantity Selector (Event Detail Page)
    const qtyInput = document.getElementById('quantity-input');
    if (qtyInput) {
        const minusBtn = document.querySelector('.qty-btn-minus');
        const plusBtn = document.querySelector('.qty-btn-plus');
        const totalDisplay = document.getElementById('total-price-display');
        const price = parseFloat(qtyInput.getAttribute('data-price'));
        const max = parseInt(qtyInput.getAttribute('data-max'));

        const updateTotal = () => {
            let val = parseInt(qtyInput.value);
            if (isNaN(val) || val < 1) val = 1;
            if (val > max) val = max;
            qtyInput.value = val;
            
            if (totalDisplay) {
                totalDisplay.textContent = (val * price).toFixed(2);
            }
        };

        if (minusBtn) {
            minusBtn.addEventListener('click', () => {
                let val = parseInt(qtyInput.value);
                if (val > 1) {
                    qtyInput.value = val - 1;
                    updateTotal();
                }
            });
        }

        if (plusBtn) {
            plusBtn.addEventListener('click', () => {
                let val = parseInt(qtyInput.value);
                if (val < max) {
                    qtyInput.value = val + 1;
                    updateTotal();
                }
            });
        }

        qtyInput.addEventListener('input', updateTotal);
        qtyInput.addEventListener('blur', updateTotal);
    }

    // 5. Print Ticket
    const printBtn = document.getElementById('print-ticket-btn');
    if (printBtn) {
        printBtn.addEventListener('click', () => {
            window.print();
        });
    }

    // 6. Animate on Scroll
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // 7. Card Hover Parallax Effect (Optional premium touch)
    const cards = document.querySelectorAll('.event-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = ((y - centerY) / centerY) * -5;
            const rotateY = ((x - centerX) / centerX) * 5;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = `perspective(1000px) rotateX(0) rotateY(0) translateY(0)`;
        });
    });
});
