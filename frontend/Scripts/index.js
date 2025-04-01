const baseUrl = 'http://localhost:8000'

document.addEventListener('DOMContentLoaded', async () => {
    // Set initial opacity
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.1s';
    
    const accessToken = localStorage.getItem('access_token');
    
    // Redirect if not logged in
    if (!accessToken) {
        window.location.href = 'login.html';
        return;
    }
    
    // Xử lý form deposit
    const depositForm = document.getElementById('depositForm');
    if (depositForm) {
        depositForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const walletAddress = document.getElementById('depositWallet').value;
            const amount = document.getElementById('depositAmount').value;
            const privatePassword = document.getElementById('depositPrivatePassword').value;

            if (!walletAddress || !amount) {
                alert('Please fill in all required fields');
                return;
            }
            
            // Kiểm tra private password
            const storedPrivatePassword = localStorage.getItem('private_password');
            if (privatePassword !== storedPrivatePassword) {
                alert('Incorrect private password');
                return;
            }

            // Hiển thị loading
            const submitButton = depositForm.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
            
            console.log('Attempting to deposit', {
                wallet_address: walletAddress,
                amount: parseFloat(amount)
            });
            
            // Thực hiện nạp tiền
            fetch(`${baseUrl}/api/wallets/deposit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    wallet_address: walletAddress,
                    amount: parseFloat(amount)
                })
            })
            .then(response => {
                console.log('Deposit response status:', response.status);
                return response.json();
            })
            .then(result => {
                console.log('Deposit result:', result);
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                if (result.status === 'success') {
                    // Thông báo thành công
                    alert(`Deposit completed successfully!\nTransaction hash: ${result.transaction_hash || result.hash || ''}`);
                    
                    // Đóng modal
                    const modal = document.getElementById('depositModal');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    
                    // Reset form
                    depositForm.reset();
                    
                    // Refresh dữ liệu
                    loadWallets();
                } else {
                    // Thông báo lỗi
                    alert(`Deposit failed: ${result.message}`);
                }
            })
            .catch(error => {
                console.error('Deposit error:', error);
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                // Thông báo lỗi
                alert(`Error: ${error.message}`);
            });
        });
    }

    // Parse user info with better error handling
    const userInfo = (() => {
        try {
            return JSON.parse(localStorage.getItem('user_info') || '{}');
        } catch (error) {
            console.error('Lỗi parse user_info:', error);
            return {};
        }
    })();
    
    try {
        // Load data in parallel
        await Promise.all([loadWallets(), loadTransactions()]);
        
        // Update UI
        updateUserInfo();
        updateWalletDropdowns();
        setupTabListeners();
        
        // Show the page
        document.body.style.opacity = '1';
    } catch (error) {
        console.error('Lỗi tải dữ liệu:', error, error.stack);
        
        // Show a more specific error message
        alert(`Lỗi tải dữ liệu: ${error.message || 'Không xác định'}`);
        
        // Still show the page even if there's an error
        document.body.style.opacity = '1';
    }
});

function updateUserInfo() {
    // Lấy thông tin người dùng từ localStorage một cách hiệu quả hơn
    const userInfo = (() => {
        try {
            return JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
        } catch (error) {
            console.error('Lỗi khi parse thông tin người dùng:', error);
            return {};
        }
    })();
    
    // Kiểm tra và thoát sớm nếu không có thông tin
    if (!userInfo?.name) {
        console.error('Không tìm thấy thông tin người dùng hoặc không đầy đủ:', userInfo);
        return;
    }
    
    // Chuẩn bị giá trị mặc định
    const userName = userInfo.name || 'Người dùng';
    const userEmail = userInfo.email || '';
    
    // Cập nhật tên người dùng
    document.querySelectorAll('.user-name').forEach(el => el.textContent = userName);
    
    // Cập nhật "Hello, [tên]"
    document.querySelectorAll('.profile-info h6').forEach(el => el.textContent = `Hello, ${userName}`);
    
    // Cập nhật email
    document.querySelectorAll('.user-email').forEach(el => el.textContent = userEmail);
    
    // Cập nhật các phần tử theo ID - sử dụng ID chọn lọc
    const idSelectors = {
        'headerUserEmail': userEmail,
        'settingsUserName': userName,
        'settingsUserEmail': userEmail
    };
    
    Object.entries(idSelectors).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
    
    // Cập nhật ảnh đại diện
    if (userInfo.profileImage) {
        
        let imagePath = userInfo.profileImage;
        if (!imagePath.startsWith('/') && !imagePath.startsWith('http')) {
            imagePath = `/static/${imagePath}`;
        }
        
        const fullImagePath = `${baseUrl}${imagePath}`;
        
        document.querySelectorAll('.profile-img').forEach(img => {
            img.src = fullImagePath;
            img.style.display = 'block';
        });
    }
}

function setupTabListeners() {
    // Sử dụng delegation (ủy quyền sự kiện) thay vì gắn nhiều event listeners
    document.addEventListener('shown.bs.tab', function(event) {
        if (!event.target.hasAttribute('data-bs-toggle')) return;
        
        const targetId = event.target.getAttribute('href');
        
        // Sử dụng object mapping để xử lý các tab một cách nhất quán
        const tabActions = {
            '#transactions': 'transactionTable',
            '#dashboard': 'walletTable'
        };
        
        // Kiểm tra nếu tab hiện tại nằm trong danh sách cần xử lý
        const elementId = tabActions[targetId];
        if (elementId) {
            const element = document.getElementById(elementId);
            if (element) {
                element.style.opacity = '1';
            }
        }
    });
}

// Tải danh sách ví - với bộ nhớ đệm
let cachedWallets = null;
function loadWallets() {
    // Xóa cache để luôn tải mới
    cachedWallets = null;
    
    // Lấy thông tin user từ localStorage - kiểm tra cả hai key
    const userInfo = JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    console.log('Loading wallets with user info:', userInfo);
    console.log('Token available:', !!accessToken);
    
    if (!userInfo?.id || !accessToken) {
        console.error('Thiếu thông tin người dùng hoặc token');
        return Promise.reject(new Error('Thiếu thông tin người dùng'));
    }
    
    console.log('Loading wallets for user ID:', userInfo.id);
    
    // Hiển thị trạng thái đang tải
    const walletList = document.getElementById('walletList');
    if (walletList) {
        walletList.innerHTML = '<tr><td colspan="5" class="text-center">Đang tải danh sách ví...</td></tr>';
    }
    
    const apiUrl = `${baseUrl}/api/wallets/user/${userInfo.id}`;
    console.log('Fetching from URL:', apiUrl);
    
    return fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        mode: 'cors' // Đảm bảo yêu cầu CORS được gửi đúng
    })
    .then(response => {
        console.log('Wallet list response status:', response.status);
        if (!response.ok) {
            if (response.status === 401) {
                // Token hết hạn, đăng xuất
                localStorage.removeItem('access_token');
                localStorage.removeItem('token');
                localStorage.removeItem('user_info');
                localStorage.removeItem('user');
                window.location.href = 'login.html';
                return;
            }
            throw new Error(`Lỗi kết nối: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallets API response:', data);
        
        // Lưu vào bộ nhớ đệm - lưu cả đối tượng phản hồi
        cachedWallets = data;
        
        // Hiển thị lên giao diện
        renderWallets(data);
        
        return data;
    })
    .catch(error => {
        console.error('Lỗi khi tải ví:', error);
        
        // Kiểm tra lỗi CORS
        if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            console.error('Có thể là lỗi CORS. Hãy đảm bảo backend đã bật CORS và đang chạy.');
            
            // Hiển thị hướng dẫn khắc phục
            if (walletList) {
                walletList.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-danger">
                            <p>Lỗi kết nối đến API: ${error.message}</p>
                            <p>Có thể là lỗi CORS hoặc server chưa khởi động.</p>
                            <p>Hãy đảm bảo server backend đang chạy tại http://127.0.0.1:8000</p>
                            <button class="btn btn-primary mt-2" onclick="loadWallets()">Thử lại</button>
                        </td>
                    </tr>
                `;
            }
        } else {
            // Hiển thị thông báo lỗi trên UI
            if (walletList) {
                walletList.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error loading wallets: ${error.message}</td></tr>`;
            }
        }
        
        return [];
    });
}

// Hiển thị danh sách ví
function renderWallets(wallets) {
    console.log('Rendering wallets:', wallets);
    
    // Try multiple possible selectors for the wallet list
    let walletList = document.getElementById('walletList');
    
    if (!walletList) {
        console.log('walletList ID not found, trying alternative selectors');
        
        // Try to find the table body with a different selector
        walletList = document.querySelector('#walletTable tbody');
        
        if (!walletList) {
            console.log('Table body not found, trying to find the table');
            const walletTable = document.getElementById('walletTable');
            
            if (!walletTable) {
                console.log('Wallet table not found, trying to find any table in the dashboard');
                const dashboardSection = document.getElementById('dashboard');
                
                if (dashboardSection) {
                    console.log('Dashboard section found, looking for tables');
                    const tables = dashboardSection.querySelectorAll('table');
                    
                    if (tables.length > 0) {
                        console.log('Found a table in dashboard, using the first one');
                        const table = tables[0];
                        
                        // Check if the table has a tbody
                        let tbody = table.querySelector('tbody');
                        
                        if (!tbody) {
                            console.log('Table has no tbody, creating one');
                            tbody = document.createElement('tbody');
                            table.appendChild(tbody);
                        }
                        
                        walletList = tbody;
                    } else {
                        console.log('No tables found in dashboard, creating a new table');
                        // Create a new table in the dashboard section
                        const newTable = document.createElement('table');
                        newTable.id = 'walletTable';
                        newTable.className = 'table table-striped';
                        
                        // Create table header
                        const thead = document.createElement('thead');
                        thead.innerHTML = `
                            <tr>
                                <th>Label</th>
                                <th>Balance</th>
                                <th>Address</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        `;
                        newTable.appendChild(thead);
                        
                        // Create table body
                        const tbody = document.createElement('tbody');
                        tbody.id = 'walletList';
                        newTable.appendChild(tbody);
                        
                        // Add the table to the dashboard
                        dashboardSection.appendChild(newTable);
                        
                        walletList = tbody;
                    }
                } else {
                    console.error('Dashboard section not found, cannot create wallet table');
                    
                    // Last resort: try to find any container to add the table
                    const mainContent = document.querySelector('.main-content') || document.querySelector('main') || document.body;
                    
                    if (mainContent) {
                        console.log('Found main content area, creating wallet table');
                        
                        // Create a container for the wallet table
                        const walletSection = document.createElement('div');
                        walletSection.className = 'wallet-section mt-4';
                        
                        // Create a heading
                        const heading = document.createElement('h3');
                        heading.textContent = 'My Wallets';
                        walletSection.appendChild(heading);
                        
                        // Create the table
                        const newTable = document.createElement('table');
                        newTable.id = 'walletTable';
                        newTable.className = 'table table-striped';
                        
                        // Create table header
                        const thead = document.createElement('thead');
                        thead.innerHTML = `
                            <tr>
                                <th>Label</th>
                                <th>Balance</th>
                                <th>Address</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        `;
                        newTable.appendChild(thead);
                        
                        // Create table body
                        const tbody = document.createElement('tbody');
                        tbody.id = 'walletList';
                        newTable.appendChild(tbody);
                        
                        // Add the table to the section
                        walletSection.appendChild(newTable);
                        
                        // Add the section to the main content
                        mainContent.appendChild(walletSection);
                        
                        walletList = tbody;
                    } else {
                        console.error('Could not find any suitable container for wallet table');
                        return;
                    }
                }
            } else {
                console.log('Wallet table found, creating tbody');
                const tbody = document.createElement('tbody');
                tbody.id = 'walletList';
                walletTable.appendChild(tbody);
                walletList = tbody;
            }
        } else {
            console.log('Found wallet table body');
        }
    }
    
    if (!walletList) {
        console.error('Could not find or create wallet list element after all attempts');
        return;
    }
    
    console.log('Using wallet list element:', walletList);
    
    // Now render the wallets to the found/created element
    renderWalletsToElement(walletList, wallets);
}

// Helper function to render wallets to a specific element
function renderWalletsToElement(element, wallets) {
    // Xóa danh sách cũ
    element.innerHTML = '';
    
    // Kiểm tra cấu trúc dữ liệu trả về từ API
    // API trả về { status: 'success', wallets: [...] }
    const walletArray = wallets.wallets || wallets;
    
    if (!walletArray || walletArray.length === 0) {
        element.innerHTML = '<tr><td colspan="5" class="text-center">No wallets found</td></tr>';
        return;
    }
    
    console.log('Processing wallet array:', walletArray);
    
    // Hiển thị danh sách ví
    walletArray.forEach(wallet => {
        try {
            console.log('Processing wallet:', wallet);
            
            // Format creation date
            let creationDate = 'N/A';
            if (wallet.created_at) {
                try {
                    creationDate = new Date(wallet.created_at).toLocaleString();
                } catch (e) {
                    console.error('Error formatting date:', e);
                }
            }
            
            // Ensure we have a valid label
            const walletLabel = wallet.label && wallet.label.trim() !== '' ? wallet.label : 'My Wallet';
            console.log('Wallet label:', walletLabel);
            
            // Create row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${walletLabel}</td>
                <td>${wallet.balance || 0} ETH</td>
                <td>${wallet.address || 'N/A'}</td>
                <td>${creationDate}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="revealWallet('${wallet.address}')">Reveal Key</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteWallet(${wallet.id})">Delete</button>
                </td>
            `;
            element.appendChild(row);
        } catch (error) {
            console.error('Error rendering wallet:', error, wallet);
        }
    });
}

// Tải danh sách giao dịch - với bộ nhớ đệm
let cachedTransactions = null;
function loadTransactions() {
    if (cachedTransactions) {
        renderTransactions(cachedTransactions);
        return Promise.resolve(cachedTransactions);
    }
    
    // Lấy thông tin user từ localStorage
    const userInfo = JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    if (!userInfo?.id || !accessToken) {
        console.error('Thiếu thông tin người dùng hoặc token');
        return Promise.reject(new Error('Thiếu thông tin người dùng'));
    }
    
    const tbody = document.getElementById('transactionTableBody');
    if (!tbody) return Promise.resolve([]);
    
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Đang tải giao dịch...</td></tr>';
    
    // Lấy danh sách ví của người dùng - sửa đường dẫn API
    return fetch(`${baseUrl}/api/wallets/user/${userInfo.id}`, {
        method: 'GET',
            headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Không thể tải danh sách ví');
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallet data for transactions:', data);
        
        // Check if we have wallets in the response
        const wallets = data.wallets || data;
        
        if (!wallets || !Array.isArray(wallets) || wallets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có ví nào. Hãy tạo ví trước!</td></tr>';
            return [];
        }
        
        // Lấy địa chỉ của tất cả các ví
        const walletAddresses = wallets.map(wallet => wallet.address);
        
        // Lấy giao dịch cho mỗi ví
        const promises = walletAddresses.map(address => 
            fetch(`${baseUrl}/api/transactions/${address}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    console.error(`Lỗi khi tải giao dịch cho ví ${address}: ${response.status}`);
                    return []; // Trả về mảng rỗng thay vì báo lỗi
                }
                return response.json();
            })
            .catch(error => {
                console.error(`Lỗi khi tải giao dịch cho ví ${address}:`, error);
                return []; // Trả về mảng rỗng khi có lỗi
            })
        );
        
        // Kết hợp tất cả các giao dịch
        return Promise.all(promises)
            .then(results => {
                // Làm phẳng mảng
                let allTransactions = [];
                results.forEach(result => {
                    if (Array.isArray(result)) {
                        allTransactions = allTransactions.concat(result);
                    }
                });
                
                // Sắp xếp theo ngày (mới nhất trước)
                allTransactions.sort((a, b) => {
                    const dateA = new Date(a.created_at || 0);
                    const dateB = new Date(b.created_at || 0);
                    return dateB - dateA;
                });
                
                // Lưu vào bộ nhớ đệm
                cachedTransactions = allTransactions;
                
                return allTransactions;
            });
    })
    .then(transactions => {
        // Hiển thị giao dịch
        renderTransactions(transactions);
        return transactions;
    })
    .catch(error => {
        console.error('Lỗi khi tải giao dịch:', error);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">Lỗi khi tải giao dịch</td></tr>';
        }
        return [];
    });
}

// Hiển thị danh sách giao dịch
function renderTransactions(transactions) {
    const tbody = document.getElementById('transactionTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!transactions || transactions.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.textContent = 'Không tìm thấy giao dịch';
        td.className = 'text-center';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }
    
    transactions.forEach(tx => {
        const tr = document.createElement('tr');
        
        // Ngày
        const dateTd = document.createElement('td');
        dateTd.textContent = tx.created_at ? 
            new Date(tx.created_at).toLocaleDateString() : 
            'N/A';
        
        // Từ
        const fromTd = document.createElement('td');
        fromTd.textContent = tx.from_wallet ? 
            `${tx.from_wallet.substring(0,6)}...${tx.from_wallet.slice(-4)}` : 
            'N/A';
        
        // Đến
        const toTd = document.createElement('td');
        toTd.textContent = tx.to_wallet ? 
            `${tx.to_wallet.substring(0,6)}...${tx.to_wallet.slice(-4)}` : 
            'N/A';
        
        // Số tiền
        const amountTd = document.createElement('td');
        if (tx.amount) {
            const amount = parseFloat(tx.amount).toFixed(4);
            amountTd.textContent = `${amount} ETH`;
        } else {
            amountTd.textContent = '0.0000 ETH';
        }
        
        // Loại
        const typeTd = document.createElement('td');
        typeTd.textContent = tx.type || 'Không xác định';
        
        // Trạng thái
        const statusTd = document.createElement('td');
        statusTd.textContent = 'Thành công';
        
        // Ghép các cột vào dòng
        tr.appendChild(dateTd);
        tr.appendChild(fromTd);
        tr.appendChild(toTd);
        tr.appendChild(amountTd);
        tr.appendChild(typeTd);
        tr.appendChild(statusTd);
        
        tbody.appendChild(tr);
    });
}

// Cập nhật các dropdown chọn ví
function updateWalletDropdowns() {
    console.log('Updating wallet dropdowns');
    
    // Lấy thông tin user từ localStorage
    const userInfo = JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    if (!userInfo?.id || !accessToken) {
        console.error('Thiếu thông tin người dùng hoặc token');
        return;
    }
    
    // Sử dụng dữ liệu đã lưu trong bộ nhớ đệm nếu có
    if (cachedWallets) {
        console.log('Using cached wallets for dropdowns');
        populateWalletDropdowns(cachedWallets);
        return;
    }
    
    // Nếu chưa có dữ liệu trong bộ nhớ đệm, tải mới
    console.log('No cached wallets, loading from API');
    
    const apiUrl = `${baseUrl}/api/wallets/user/${userInfo.id}`;
    console.log('Fetching from URL:', apiUrl);
    
    fetch(apiUrl, {
        method: 'GET',
            headers: {
            'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        mode: 'cors' // Đảm bảo yêu cầu CORS được gửi đúng
    })
    .then(response => {
        console.log('Dropdown wallet response status:', response.status);
        if (!response.ok) {
            throw new Error(`Lỗi kết nối: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallet data for dropdowns:', data);
        // Lưu vào bộ nhớ đệm
        cachedWallets = data;
        // Cập nhật các dropdown
        populateWalletDropdowns(data);
    })
    .catch(error => {
        console.error('Lỗi khi tải ví cho dropdown:', error);
        
        // Kiểm tra lỗi CORS
        if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            console.error('Có thể là lỗi CORS. Hãy đảm bảo backend đã bật CORS và đang chạy.');
            
            // Hiển thị thông báo trong dropdown
            const dropdowns = document.querySelectorAll('.wallet-dropdown, #fromWallet, #toWallet, #depositWallet, #exportWallet');
            dropdowns.forEach(dropdown => {
                if (dropdown) {
                    dropdown.innerHTML = '<option value="">Lỗi kết nối đến API</option>';
                }
            });
        } else {
            // Hiển thị thông báo lỗi khác
            const dropdowns = document.querySelectorAll('.wallet-dropdown, #fromWallet, #toWallet, #depositWallet, #exportWallet');
            dropdowns.forEach(dropdown => {
                if (dropdown) {
                    dropdown.innerHTML = `<option value="">Lỗi: ${error.message}</option>`;
                }
            });
        }
    });
}

// Điền dữ liệu vào các dropdown
function populateWalletDropdowns(data) {
    console.log('Raw data for dropdowns:', data);
    
    // Đảm bảo mảng wallets tồn tại
    const wallets = Array.isArray(data) ? data : 
                  (data && Array.isArray(data.wallets) ? data.wallets : []);
    
    console.log('Processed wallets array:', wallets);
    
    // Xử lý From Wallet trong transfer modal
    const fromWalletSelect = document.getElementById('fromWallet');
    if (fromWalletSelect) {
        fromWalletSelect.innerHTML = '';
        
        if (wallets.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No wallets available';
            option.disabled = true;
            option.selected = true;
            fromWalletSelect.appendChild(option);
        } else {
            wallets.forEach(wallet => {
                if (wallet && wallet.address) {
                    const option = document.createElement('option');
                    option.value = wallet.address;
                    // Định dạng số để hiển thị tối đa 4 chữ số thập phân
                    const balance = parseFloat(wallet.balance || 0).toFixed(4);
                    // Rút gọn địa chỉ ví để hiển thị
                    const shortAddress = wallet.address.substring(0, 8) + '...';
                    option.textContent = `${wallet.label || 'Wallet'} (${balance} ETH) - ${shortAddress}`;
                    fromWalletSelect.appendChild(option);
                }
            });
        }
    }
    // THÊM Ở ĐÂY: Xử lý Deposit Wallet dropdown
    const depositWalletSelect = document.getElementById('depositWallet');
    if (depositWalletSelect) {
        depositWalletSelect.innerHTML = '';
        
        if (wallets.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No wallets available';
            option.disabled = true;
            option.selected = true;
            depositWalletSelect.appendChild(option);
        } else {
            wallets.forEach(wallet => {
                if (wallet && wallet.address) {
                    const option = document.createElement('option');
                    option.value = wallet.address;
                    // Định dạng số để hiển thị tối đa 4 chữ số thập phân
                    const balance = parseFloat(wallet.balance || 0).toFixed(4);
                    // Rút gọn địa chỉ ví để hiển thị
                    const shortAddress = wallet.address.substring(0, 8) + '...';
                    option.textContent = `${wallet.label || 'Wallet'} (${balance} ETH) - ${shortAddress}`;
                    depositWalletSelect.appendChild(option);
                }
            });
        }
    }
    console.log('Wallet dropdowns populated successfully');
}

function createWallet() {
    console.log('Creating new wallet');
   
    // Lấy thông tin user từ localStorage
    const userInfo = JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
   
    if (!userInfo?.id || !accessToken) {
        console.error('Thiếu thông tin người dùng hoặc token');
        alert('Bạn cần đăng nhập để tạo ví');
        return;
    }
   
    // Lấy tên ví từ form - kiểm tra element tồn tại
    
    const walletLabelElement = document.getElementById('walletLabel');
    const walletLabel = walletLabelElement && walletLabelElement.value.trim() !== ''
        ? walletLabelElement.value.trim()
        : 'My Wallet';
   
    console.log('Creating wallet with label:', walletLabel);
   
    // Hiển thị trạng thái đang tạo
    const createButton = document.querySelector('#createWalletForm button[type="submit"]');
    let originalText = 'Create Wallet';
   
    if (createButton) {
        originalText = createButton.innerHTML;
        createButton.disabled = true;
        createButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';
    }
   
    console.log('Sending wallet creation request with data:', {
        user_id: userInfo.id,
        label: walletLabel
    });
   
    // Gửi yêu cầu tạo ví mới
    fetch(`${baseUrl}/api/wallets/create`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userInfo.id,
            label: walletLabel
        })
    })
    .then(response => {
        debugger;
        console.log('Create wallet response status:', response.status);
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || `Lỗi kết nối: ${response.status} ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallet created successfully:', data);
       
        // Đóng modal - sửa từ createWalletModal thành createModal
        const modalElement = document.getElementById('createModal');
        if (modalElement) {
            try {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                } else {
                    // Fallback if bootstrap.Modal is not available
                    $(modalElement).modal('hide');
                }
            } catch (error) {
                console.error('Error closing modal:', error);
                // Another fallback method
                $(modalElement).modal('hide');
            }
        }
       
        // Reset form
        if (walletLabelElement) {
            walletLabelElement.value = '';
        }
       
        // Tải lại danh sách ví
        loadWallets().then(() => {
            // Cập nhật các dropdown
            updateWalletDropdowns();
           
            // Hiển thị thông báo thành công
            alert('Ví mới đã được tạo thành công!');
        });
    })
    .catch(error => {
        console.error('Lỗi khi tạo ví:', error);
        alert(`Lỗi khi tạo ví: ${error.message}`);
    })
    .finally(() => {
        // Khôi phục trạng thái nút
        if (createButton) {
            createButton.disabled = false;
            createButton.innerHTML = originalText;
        }
    });
}

// // Handle Change Password
// document.getElementById('changePasswordForm')?.addEventListener('submit', async function(e) {
//     e.preventDefault();
//     const currentPassword = document.getElementById('currentPassword').value;
//     const newPassword = document.getElementById('newPassword').value;
    
//     if (!currentPassword || !newPassword) return;
    
//     try {
//         const response = await fetch(`${baseUrl}/api/auth/change-password`, {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'Authorization': `Bearer ${accessToken}`
//             },
//             body: JSON.stringify({
//                 current_password: currentPassword,
//                 new_password: newPassword
//             })
//         });
        
//         if (!response.ok) throw new Error('Failed to change password');
        
//         bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
//         alert('Password changed successfully!');
        
//     } catch (error) {
//         console.error('Error changing password:', error);
//         alert('Failed to change password. Please try again.');
//     }
// });



// Handle Logout
function handleLogout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    window.location.href = 'login.html';
}

// Add event listener for logout button
document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);

// Handle change name form
$('#changeNameForm').on('submit', function(e) {
    e.preventDefault();
    
    const newName = $('#newName').val();
    console.log('Form submitted with new name:', newName);

    // 2. Gửi request lên server để update
    $.ajax({
        url: `${baseUrl}/api/auth/change-name`,
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        data: JSON.stringify({
            new_name: newName
        }),
        success: function(response) {
            console.log('Server response:', response);
            if (response.status === 'success') {
                // 3. Server trả về thành công, update localStorage
                const userInfo = JSON.parse(localStorage.getItem('user_info'));
                console.log('Before update:', userInfo);
                userInfo.name = response.user.name;  // Dùng tên từ response
                localStorage.setItem('user_info', JSON.stringify(userInfo));
                console.log('After update:', JSON.parse(localStorage.getItem('user_info')));
                
                // 4. Update UI với tên mới
                $('.profile-info h6').text(`Hello, ${response.user.name}`);
                $('#settingsUserName').text(response.user.name);
                
                // 5. Đóng modal và thông báo
                $('#changeNameModal').modal('hide');
                $('#newName').val(''); // Clear form
                alert('Name updated successfully!');
            }
        },
        error: function(xhr, status, error) {
            console.error('Error details:', {
                status: status,
                error: error,
                response: xhr.responseText
            });
            alert('Failed to update name');
        }
    });
});



// Đảm bảo code được thực thi sau khi DOM đã tải xong
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo modal (nếu sử dụng Bootstrap)
    const changeImageModal = new bootstrap.Modal(document.getElementById('changeImageModal'));
    
    // Handle Change Image form submission
    const changeImageForm = document.getElementById('changeImageForm');
    if (changeImageForm) {
        changeImageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const imageFile = document.getElementById('newImage').files[0];
            console.log('Form submitted, selected file:', imageFile);
            
            if (!imageFile) {
                alert('Please select an image file');
                return;
            }
            
            const formData = new FormData();
            formData.append('profile_image', imageFile);
            
            fetch(`${baseUrl}/api/auth/change-image`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    // Không thêm Content-Type vào đây vì browser sẽ tự thêm khi sử dụng FormData
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log('Success:', data);
                if (data.status === 'success') {
                    // Update profile images in UI
                    const newImagePath = data.user.profileImage;
                    console.log('New image path from server:', newImagePath);
                    
                    document.querySelectorAll('.profile-img').forEach(img => {
                        // Kiểm tra đường dẫn và xử lý phù hợp
                        if (newImagePath.startsWith('http')) {
                            // Đường dẫn đã đầy đủ
                            img.src = newImagePath;
                        } else if (newImagePath.startsWith('/')) {
                            // Đường dẫn bắt đầu bằng /
                            img.src = `${baseUrl}${newImagePath}`;
                        } else {
                            // Đường dẫn tương đối
                            img.src = `${baseUrl}/${newImagePath}`;
                        }
                        img.style.display = 'block';
                        console.log('Set profile image to:', img.src);
                    });
                    
                    // Store image path in localStorage
                    try {
                        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
                        userInfo.profileImage = newImagePath;
                        localStorage.setItem('user_info', JSON.stringify(userInfo));
                    } catch (error) {
                        console.error('Lỗi khi cập nhật localStorage:', error);
                    }
                    
                    // Close modal and clear form
                    $('#changeImageModal').modal('hide');
                    document.getElementById('newImage').value = '';
                    alert('Profile image updated successfully!');
                } else {
                    alert('Failed to update profile image: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to update profile image: ' + error.message);
            });
        });
    } else {
        console.error('Change image form not found in the document');
    }
});
// Xử lý form transfer đơn giản và ổn định
document.addEventListener('DOMContentLoaded', function() {
    // Xử lý form transfer
    const transferForm = document.getElementById('transferForm');
    if (transferForm) {
        transferForm.addEventListener('submit', function(e) {
            e.preventDefault();
           
            const fromWallet = document.getElementById('fromWallet').value;
            const toWallet = document.getElementById('toWallet').value;
            const amount = document.getElementById('transferAmount').value;
            const transferPrivatePassword = document.getElementById('transferPrivatePassword').value;
            const confirmTransfer = document.getElementById('confirmTransfer')?.checked || false;
           
            // Debug: Kiểm tra các giá trị
            console.log('From Wallet:', fromWallet);
            console.log('To Wallet:', toWallet);
            console.log('Amount:', amount);
            console.log('Transfer Private Password:', transferPrivatePassword);
            console.log('Confirm Transfer:', confirmTransfer);
           
            if (!fromWallet || !toWallet || !amount) {
                alert('Please fill in all required fields');
                return;
            }
           
            if (!confirmTransfer) {
                alert('Please confirm the transaction');
                return;
            }
           
            // Kiểm tra private password
            const storedPrivatePassword = localStorage.getItem('private_password');
            console.log('Stored Private Password:', storedPrivatePassword);
            
            if (transferPrivatePassword !== storedPrivatePassword) {
                alert('Incorrect private password');
                return;
            }
            // Hiển thị loading
            const submitButton = transferForm.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
            
            // Thực hiện chuyển tiền
            fetch('http://127.0.0.1:8000/api/wallets/transfer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    from_wallet: fromWallet,
                    to_wallet: toWallet,
                    amount: parseFloat(amount),
                    confirm: true
                })
            })
            .then(response => response.json())
            .then(result => {
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                if (result.status === 'success') {
                    // Thông báo thành công
                    alert(`Transfer completed successfully!\nTransaction hash: ${result.transaction_hash}`);
                    
                    // Đóng modal
                    const modal = document.getElementById('transferModal');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    
                    // Reset form
                    transferForm.reset();
                    
                    // Refresh dữ liệu
                    loadWallets();
                } else {
                    // Thông báo lỗi
                    alert(`Transfer failed: ${result.message}`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
                
                // Thông báo lỗi
                alert(`Error: ${error.message}`);
            });
        });
    }
    
});

// Handle Search Form
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    
    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Ngăn modal từ việc tự đóng
            e.stopPropagation();
            
            const keyword = document.getElementById('searchKeyword').value.trim();
            if (!keyword) {
                alert('Please enter a wallet address to search');
                return;
            }
            
            const token = localStorage.getItem('access_token');
            const resultsDiv = document.getElementById('searchResults');
            
            // Hiển thị trạng thái đang tìm kiếm
            resultsDiv.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Searching transactions...</p></div>';
            
            try {
                const response = await fetch(`${baseUrl}/api/transactions/${keyword}`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`Error: ${response.status} ${response.statusText}`);
                }
                
                const results = await response.json();
                console.log('Search results:', results);
                
                // Xóa trạng thái loading
                resultsDiv.innerHTML = '';
                
                // Kiểm tra kết quả
                if (!results || results.length === 0) {
                    resultsDiv.innerHTML = '<div class="alert alert-info">No transactions found for this wallet address</div>';
                    return;
                }
                
                // Tạo bảng kết quả
                const table = document.createElement('table');
                table.className = 'table table-striped table-bordered mt-3';
                
                // Tạo header
                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr class="table-dark">
                        <th>From</th>
                        <th>To</th>
                        <th>Amount</th>
                        <th>Type</th>
                        <th>Date</th>
                    </tr>
                `;
                table.appendChild(thead);
                
                // Tạo body
                const tbody = document.createElement('tbody');
                results.forEach(tx => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${tx.from_wallet ? tx.from_wallet.substring(0,6) + '...' + tx.from_wallet.slice(-4) : 'N/A'}</td>
                        <td>${tx.to_wallet ? tx.to_wallet.substring(0,6) + '...' + tx.to_wallet.slice(-4) : 'N/A'}</td>
                        <td>${parseFloat(tx.amount).toFixed(4)} ETH</td>
                        <td><span class="badge ${tx.type === 'deposit' ? 'bg-success' : tx.type === 'transfer' ? 'bg-primary' : 'bg-secondary'}">${tx.type || 'Unknown'}</span></td>
                        <td>${tx.created_at ? new Date(tx.created_at).toLocaleString() : 'N/A'}</td>
                    `;
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);
                
                // Thêm thông tin tổng số giao dịch
                const resultSummary = document.createElement('div');
                resultSummary.className = 'alert alert-success';
                resultSummary.innerHTML = `Found <strong>${results.length}</strong> transaction(s) for wallet address <strong>${keyword}</strong>`;
                
                // Hiển thị kết quả
                resultsDiv.appendChild(resultSummary);
                resultsDiv.appendChild(table);
                
                // Đảm bảo modal vẫn mở
                const searchModal = bootstrap.Modal.getInstance(document.getElementById('searchModal'));
                if (!searchModal) {
                    // Nếu modal chưa được khởi tạo, khởi tạo nó
                    new bootstrap.Modal(document.getElementById('searchModal')).show();
                }
            } catch (error) {
                console.error('Error searching transactions:', error);
                resultsDiv.innerHTML = `<div class="alert alert-danger">Error searching transactions: ${error.message}</div>`;
            }
        });
    }
});

// Handle Export Form
document.getElementById('exportForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const walletAddress = document.getElementById('exportWallet').value;
    const format = document.getElementById('exportFormat').value;
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await fetch(`${baseUrl}/api/wallets/export?wallet_address=${walletAddress}&format=${format}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        console.log('Export result:', result);
        
        if (result.status === 'success') {
            alert(`Data exported successfully to ${result.file}`);
            bootstrap.Modal.getInstance(document.getElementById('exportModal')).hide();
        } else {
            alert('Export failed: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
});



// Handle Reveal Wallet
document.getElementById('revealWalletForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const walletAddress = localStorage.getItem('currentWalletAddress');
    const inputPassword = document.getElementById('walletPassword').value;
    const token = localStorage.getItem('access_token');
    
    // Lấy private password từ localStorage
    const userInfo = JSON.parse(localStorage.getItem('user_info'));
    const storedPrivatePassword = localStorage.getItem('private_password');
    
    // Kiểm tra mật khẩu nhập vào có khớp với private password đã lưu không
    if (inputPassword !== storedPrivatePassword) {
        alert('Incorrect private password. Please try again.');
        document.getElementById('walletPassword').value = '';
        return;
    }
    
    if (!walletAddress || !token) {
        alert('Missing required information');
        return;
    }
    
    try {
        // Gửi request không có private_password vì backend chưa hỗ trợ
        const response = await fetch(`${baseUrl}/api/wallets/reveal`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                wallet_address: walletAddress
                // Không gửi private_password
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to reveal wallet');
        }
        
        const result = await response.json();
        console.log('Wallet revealed:', result);
        
        // Display private key in modal
        const modal = document.getElementById('revealModal');
        const modalBody = modal.querySelector('.modal-body');
        
        // Clear previous form
        modalBody.innerHTML = '';
        
        // Create elements to display private key
        const keyContainer = document.createElement('div');
        keyContainer.className = 'alert alert-warning';
        
        const keyTitle = document.createElement('h6');
        keyTitle.textContent = 'Private Key:';
        keyTitle.className = 'mb-2';
        
        const keyValue = document.createElement('div');
        keyValue.className = 'p-2 bg-light text-dark rounded mb-3 user-select-all';
        keyValue.textContent = result.private_key;
        
        const warningText = document.createElement('p');
        warningText.className = 'small text-danger mb-0';
        warningText.textContent = 'Never share your private key with anyone! Keep it safe.';
        
        // Add close button
        const closeButton = document.createElement('button');
        closeButton.className = 'btn btn-secondary mt-3';
        closeButton.textContent = 'Close';
        closeButton.onclick = function() {
            bootstrap.Modal.getInstance(modal).hide();
        };
        
        // Append elements
        keyContainer.appendChild(keyTitle);
        keyContainer.appendChild(keyValue);
        keyContainer.appendChild(warningText);
        
        modalBody.appendChild(keyContainer);
        modalBody.appendChild(closeButton);
        
    } catch (error) {
        console.error('Error revealing wallet:', error);
        alert(error.message || 'Failed to reveal wallet. Incorrect private password.');
        
        // Reset form
        document.getElementById('walletPassword').value = '';
    }
});

// Thêm event listener cho nút tạo ví
document.addEventListener('DOMContentLoaded', function() {
    // Load wallets when page loads
    loadWallets();
    
        // Add event listener for create wallet button
    const createWalletBtn = document.getElementById('createWalletBtn');
    if (createWalletBtn) {
        createWalletBtn.addEventListener('click', function(e) {
            // Nếu nút chỉ để mở modal, không gọi createWallet
            if (createWalletBtn.getAttribute('data-bs-toggle') === 'modal') {
                // Không làm gì cả, vì nút này chỉ để mở modal
                return;
            }
            
            // Ngược lại, gọi hàm tạo ví
            e.preventDefault();
            // createWallet();
        });
    }
    
    // Add event listener for create wallet form
    const createWalletForm = document.getElementById('createWalletForm');
    if (createWalletForm) {
        createWalletForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createWallet();
        });
    }

    // Add event listener for tab changes
    const tabs = document.querySelectorAll('a[data-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const target = e.target.getAttribute('href');
            if (target === '#wallets') {
                loadWallets();
            } else if (target === '#transactions') {
                loadTransactions();
            }
        });
    });
});

// Xóa ví
function deleteWallet(walletId) {
    console.log('Deleting wallet with ID:', walletId);
    
    if (!confirm('Bạn có chắc chắn muốn xóa ví này không?')) {
        return;
    }
    
    // Lấy token từ localStorage
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    if (!accessToken) {
        console.error('Thiếu token xác thực');
        alert('Bạn cần đăng nhập để thực hiện thao tác này');
        return;
    }
    
    // Gửi yêu cầu xóa ví
    fetch(`${baseUrl}/api/wallets/${walletId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Delete wallet response status:', response.status);
        if (!response.ok) {
            throw new Error(`Lỗi kết nối: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallet deleted successfully:', data);
        
        // Tải lại danh sách ví
        loadWallets().then(() => {
            // Cập nhật các dropdown
            updateWalletDropdowns();
            
            // Hiển thị thông báo thành công
            alert('Ví đã được xóa thành công!');
        });
    })
    .catch(error => {
        console.error('Lỗi khi xóa ví:', error);
        alert(`Lỗi khi xóa ví: ${error.message}`);
    });
}

// Hiển thị khóa riêng tư của ví
function revealWallet(walletAddress) {
    console.log('Revealing wallet with address:', walletAddress);
    
    // Lấy token từ localStorage
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    if (!accessToken) {
        console.error('Thiếu token xác thực');
        alert('Bạn cần đăng nhập để thực hiện thao tác này');
        return;
    }
    
    // Gửi yêu cầu lấy thông tin ví
    fetch(`${baseUrl}/api/wallets/address/${walletAddress}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Reveal wallet response status:', response.status);
        if (!response.ok) {
            throw new Error(`Lỗi kết nối: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Wallet details retrieved:', data);
        
        // Hiển thị thông tin khóa riêng tư
        const wallet = data.wallet || data;
        if (wallet && wallet.private_key) {
            alert(`Private Key: ${wallet.private_key}\n\nLưu ý: Hãy giữ khóa riêng tư này an toàn và không chia sẻ với bất kỳ ai!`);
        } else {
            alert('Không thể lấy khóa riêng tư của ví này.');
        }
    })
    .catch(error => {
        console.error('Lỗi khi lấy thông tin ví:', error);
        alert(`Lỗi khi lấy thông tin ví: ${error.message}`);
    });
}

// Kiểm tra đăng nhập khi tải trang
function checkLogin() {
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    const userInfo = JSON.parse(localStorage.getItem('user_info') || localStorage.getItem('user') || '{}');
    
    console.log('Checking login status:', !!accessToken, userInfo);
    
    if (!accessToken) {
        console.log('No access token found, redirecting to login page');
        window.location.href = 'login.html';
        return false;
    }
    
    if (!userInfo || !userInfo.id) {
        console.log('User info missing or incomplete, redirecting to login page');
        // Xóa token không hợp lệ
        localStorage.removeItem('access_token');
        localStorage.removeItem('token');
        localStorage.removeItem('user_info');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
        return false;
    }
    
    // Hiển thị thông tin người dùng
    const userNameElement = document.getElementById('userName');
    if (userNameElement) {
        userNameElement.textContent = userInfo.name || userInfo.email || 'User';
    }
    
        // Hiển thị ảnh đại diện nếu có
    if (userInfo.profileImage) {
        console.log('Setting user avatar in checkLogin:', userInfo.profileImage);
        const userAvatarElement = document.getElementById('userAvatar');
        if (userAvatarElement) {
            // Kiểm tra đường dẫn và xử lý phù hợp
            if (userInfo.profileImage.startsWith('http')) {
                userAvatarElement.src = userInfo.profileImage;
            } else if (userInfo.profileImage.startsWith('/')) {
                userAvatarElement.src = `${baseUrl}${userInfo.profileImage}`;
            } else {
                userAvatarElement.src = `${baseUrl}/${userInfo.profileImage}`;
            }
            userAvatarElement.style.display = 'block';
            console.log('Set avatar in checkLogin to:', userAvatarElement.src);
        }
    }
    
    console.log('User is logged in:', userInfo.name || userInfo.email);
    return true;
}

// Đăng xuất
function logout() {
    console.log('Logging out');
    
    // Xóa thông tin đăng nhập
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('user');
    
    // Chuyển hướng về trang đăng nhập
    window.location.href = 'login.html';
}

// Khởi tạo trang
function initializePage() {
    console.log('Initializing dashboard page');
    
    // Kiểm tra đăng nhập
    if (!checkLogin()) {
        return;
    }
    
    // Ensure the dashboard section exists
    const dashboardSection = document.getElementById('dashboard');
    if (!dashboardSection) {
        console.log('Creating dashboard section');
        const mainContent = document.querySelector('.main-content') || document.querySelector('main') || document.body;
        
        if (mainContent) {
            const newDashboard = document.createElement('div');
            newDashboard.id = 'dashboard';
            newDashboard.className = 'tab-pane fade show active';
            
            // Create wallet section
            const walletSection = document.createElement('div');
            walletSection.className = 'card mb-4';
            
            // Create card header
            const cardHeader = document.createElement('div');
            cardHeader.className = 'card-header d-flex justify-content-between align-items-center';
            
            const headerTitle = document.createElement('h5');
            headerTitle.className = 'mb-0';
            headerTitle.textContent = 'My Wallets';
            
            const createButton = document.createElement('button');
            createButton.id = 'createWalletBtn';
            createButton.className = 'btn btn-primary btn-sm';
            createButton.textContent = 'Create New Wallet';
            createButton.setAttribute('data-bs-toggle', 'modal');
            createButton.setAttribute('data-bs-target', '#createWalletModal');
            
            cardHeader.appendChild(headerTitle);
            cardHeader.appendChild(createButton);
            walletSection.appendChild(cardHeader);
            
            // Create card body
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            
            // Create table
            const table = document.createElement('table');
            table.id = 'walletTable';
            table.className = 'table table-striped';
            
            // Create table header
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>Label</th>
                    <th>Balance</th>
                    <th>Address</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            `;
            table.appendChild(thead);
            
            // Create table body
            const tbody = document.createElement('tbody');
            tbody.id = 'walletList';
            table.appendChild(tbody);
            
            cardBody.appendChild(table);
            walletSection.appendChild(cardBody);
            
            newDashboard.appendChild(walletSection);
            mainContent.appendChild(newDashboard);
        }
    }
    
    // Tải danh sách ví
    loadWallets().then(() => {
        // Cập nhật các dropdown
        updateWalletDropdowns();
    });
    
    // Thiết lập sự kiện cho nút đăng xuất
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Thiết lập sự kiện cho nút tạo ví
    const createWalletBtn = document.getElementById('createWalletBtn');
    if (createWalletBtn) {
        createWalletBtn.addEventListener('click', function(e) {
            // Only prevent default if this is a direct click, not for modal toggle
            if (!e.target.hasAttribute('data-bs-toggle')) {
                e.preventDefault();
                createWallet();
            }
        });
    }
    
    // Thiết lập sự kiện cho nút làm mới danh sách ví
    const refreshWalletsBtn = document.getElementById('refreshWalletsBtn');
    if (refreshWalletsBtn) {
        refreshWalletsBtn.addEventListener('click', function() {
            loadWallets().then(() => {
                updateWalletDropdowns();
            });
        });
    }

};

// Chạy khởi tạo khi trang đã tải xong
document.addEventListener('DOMContentLoaded', initializePage);

// Thêm hoặc duy trì các hàm này
function getUserInfo() {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : {};
}

function getAccessToken() {
    return localStorage.getItem('access_token');
}
