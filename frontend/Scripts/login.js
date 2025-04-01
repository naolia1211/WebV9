const baseUrl = 'http://localhost:8000'

document.addEventListener('DOMContentLoaded', function() {
    // Kiểm tra nếu đã đăng nhập thì chuyển hướng
    if (localStorage.getItem('access_token') && localStorage.getItem('user_info')) {
        window.location.href = 'index.html';
        return; // Thoát sớm nếu đã đăng nhập
    }

    // Basic login without validation
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email')?.value;
            const password = document.getElementById('password')?.value;
            const privatePassword = document.getElementById('privatePassword')?.value;
            const errorMessage = document.getElementById('errorMessage');
            
            if (!email || !password) {
                if (errorMessage) {
                    errorMessage.textContent = 'Please fill in all required fields';
                    errorMessage.style.display = 'block';
                }
                return;
            }
            
            // Hide previous error message if exists
            if (errorMessage) {
                errorMessage.style.display = 'none';
            }
            
            const formData = new FormData();
            formData.append('username', email);  // OAuth2 yêu cầu tên field là 'username'
            formData.append('password', password);
            
            fetch(`${baseUrl}/api/auth/login`, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    // Nếu response không ok (status code không phải 2xx)
                    return response.json().then(data => {
                        // Lấy thông báo lỗi từ response (nếu có)
                        const message = data.detail || data.message || 'Login failed';
                        throw new Error(message);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.access_token) {
                    // Lưu token và user info
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('user_info', JSON.stringify(data.user));
                    
                    // Chuyển hướng sau khi login thành công
                    window.location.href = 'index.html';
                } else {
                    // Nếu không có access token
                    const message = data.detail || data.message || 'Login failed';
                    throw new Error(message);
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                if (errorMessage) {
                    errorMessage.textContent = error.message; // Hiển thị thông báo lỗi cụ thể
                    errorMessage.style.display = 'block';
                }
            });
        });
    }

    // Basic signup without validation
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const name = document.getElementById('signupName')?.value;
            const email = document.getElementById('signupEmail')?.value;
            const password = document.getElementById('signupPassword')?.value;
            const privatePassword = document.getElementById('privatePassword')?.value;
            
            if (!name || !email || !password) {
                const errorMessage = document.getElementById('errorMessage');
                if (errorMessage) {
                    errorMessage.textContent = 'Please fill in all required fields';
                    errorMessage.style.display = 'block';
                }
                return;
            }
            
            // Direct API call without validation
            const response = await fetch(`${baseUrl}/api/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    email: email,
                    password: password,
                    private_password: privatePassword
                })
            });
            
            // Redirect to login regardless of response
            const loginTab = document.getElementById('login-tab');
            const emailInput = document.getElementById('email');
            if (loginTab) loginTab.click();
            if (emailInput) emailInput.value = email;
        });
    }
});

function handleCreate() {
    window.location.href = "register.html";
}