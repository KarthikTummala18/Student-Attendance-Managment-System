// State Management
const state = {
    currentUser: null,
    users: [],
    attendance: [],
    leaveRequests: []
};

// DOM Elements
const loginSection = document.getElementById('loginSection');
const dashboardSection = document.getElementById('dashboardSection');
const loginForm = document.getElementById('loginForm');
const userInfo = document.getElementById('userInfo');
const logoutBtn = document.getElementById('logoutBtn');
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

// Mock Data
const mockUsers = [
    { id: 1, name: 'John Doe', email: 'john@example.com', role: 'student' },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'faculty' },
    { id: 3, name: 'Admin User', email: 'admin@example.com', role: 'admin' }
];

// Event Listeners
loginForm.addEventListener('submit', handleLogin);
logoutBtn.addEventListener('click', handleLogout);
navItems.forEach(item => item.addEventListener('click', handleNavigation));

// Login Handler
function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const role = document.getElementById('role').value;

    // Mock authentication
    const user = mockUsers.find(u => u.email === email);
    if (user && user.role === role) {
        state.currentUser = user;
        showDashboard();
        updateUI();
    } else {
        alert('Invalid credentials');
    }
}

// Logout Handler
function handleLogout() {
    state.currentUser = null;
    showLogin();
}

// Navigation Handler
function handleNavigation(e) {
    const view = e.target.dataset.view;
    showView(view);
    
    // Update active state
    navItems.forEach(item => item.classList.remove('active'));
    e.target.classList.add('active');
}

// UI Updates
function showLogin() {
    loginSection.classList.add('active');
    dashboardSection.classList.remove('active');
    loginForm.reset();
}

function showDashboard() {
    loginSection.classList.remove('active');
    dashboardSection.classList.add('active');
    
    // Show/hide admin features
    const adminElements = document.querySelectorAll('.admin-only');
    const studentElements = document.querySelectorAll('.student-only');
    
    adminElements.forEach(el => {
        el.style.display = state.currentUser.role === 'admin' ? 'block' : 'none';
    });
    
    studentElements.forEach(el => {
        el.style.display = state.currentUser.role === 'student' ? 'block' : 'none';
    });
}

function showView(viewName) {
    views.forEach(view => {
        view.classList.remove('active');
        if (view.id === `${viewName}View`) {
            view.classList.add('active');
        }
    });
}

function updateUI() {
    // Update user info
    userInfo.textContent = `${state.currentUser.name} (${state.currentUser.role})`;
    
    // Update attendance stats (mock data)
    document.getElementById('presentDays').textContent = '15';
    document.getElementById('absentDays').textContent = '2';
    document.getElementById('leaveDays').textContent = '3';
    
    // Initialize attendance chart
    initializeAttendanceChart();
}

// Chart Initialization
function initializeAttendanceChart() {
    const ctx = document.getElementById('attendanceChart').getContext('2d');
    const data = {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        datasets: [{
            label: 'Attendance Rate',
            data: [90, 85, 95, 88],
            borderColor: '#4f46e5',
            tension: 0.1
        }]
    };
    
    new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Initialize the application
showLogin();
