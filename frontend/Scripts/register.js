console.log('Script loaded'); // Kiểm tra script có được load không
const baseUrl = 'http://localhost:8000'

// Kiểm tra nếu đã đăng nhập thì chuyển hướng
if (localStorage.getItem('access_token') && localStorage.getItem('user_info')) {
    window.location.href = 'index.html';
}

document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token');
    if (token) {
        console.log('Token found in localStorage, redirecting...');
        window.location.href = 'index.html';
    }
    
    // Handle register form submission
    const registerForm = document.getElementById('registerForm');
    const errorMessage = document.getElementById('errorMessage');
    
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Lấy giá trị từ các trường
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const privatePassword = document.getElementById('privatePassword').value;
        const profileImage = document.getElementById('profileImage').files[0];
        
        // Kiểm tra confirmPassword
        if (password !== confirmPassword) {
            alert('Mật khẩu và xác nhận mật khẩu không khớp');
            return;
        }
        
        // Lưu privatePassword vào localStorage
        localStorage.setItem('privatePassword', privatePassword);
        
        // Tạo FormData và thêm các trường
        const formData = new FormData();
        formData.append('name', name);
        formData.append('email', email);
        formData.append('password', password);
        
        // Debug FormData trước khi gửi
        console.log('FormData content before appending file:');
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
        
        if (profileImage) {
            formData.append('profile_image', profileImage);
            console.log('Profile image appended:', profileImage.name, profileImage.size, profileImage.type);
        } else {
            console.log('No profile image selected');
        }
        
        try {
            console.log('Sending registration request...');
            const response = await fetch(`${baseUrl}/api/auth/register`, {
                method: 'POST',
                body: formData
            });
            
            console.log('Raw response:', response); // Kiểm tra response object
            const result = await response.json();
            console.log('Parsed response:', result); // Kiểm tra parsed JSON
            
            if (result.status === 'success') {
                alert('Đăng ký thành công!');
                // Chuyển hướng đến trang đăng nhập sau khi đăng ký thành công
                window.location.href = 'login.html';
            } else {
                errorMessage.textContent = `Lỗi: ${result.message}`;
                errorMessage.style.display = 'block';
            }
        } catch (error) {
            console.error('Lỗi đăng ký:', error);
            errorMessage.textContent = 'Có lỗi xảy ra, vui lòng thử lại';
            errorMessage.style.display = 'block';
        }
    });
    
    // Thêm event listener cho nút quay lại
    const backButton = document.getElementById('backToLogin');
    if (backButton) {
        backButton.addEventListener('click', function() {
            window.location.href = 'login.html';
        });
    }
});

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}