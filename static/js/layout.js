/* ============================================================
   AEROLINKERS - LAYOUT INTERACTIONS & UTILITIES
   ============================================================ */

document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeDropdowns();
    initializeSearch();
});

// ============================================================
// SIDEBAR INTERACTIONS
// ============================================================

function initializeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');

    if (!sidebar || !sidebarToggle) return;

    // Get sidebar state from localStorage
    const sidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarState) {
        sidebar.classList.add('collapsed');
    }

    // Toggle sidebar on hamburger click (mobile)
    sidebarToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            sidebar.classList.toggle('mobile-open');
            document.body.classList.toggle('sidebar-open');
            createOrRemoveOverlay();
        }
    });

    // Toggle sidebar collapse (desktop)
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }

    // Close mobile sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && sidebar.classList.contains('mobile-open')) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
                document.body.classList.remove('sidebar-open');
                createOrRemoveOverlay();
            }
        }
    });

    // Close mobile sidebar when nav item clicked
    const navItems = sidebar.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('mobile-open');
                document.body.classList.remove('sidebar-open');
                createOrRemoveOverlay();
            }
        });
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('mobile-open');
            document.body.classList.remove('sidebar-open');
            createOrRemoveOverlay();
        }
    });
}

function createOrRemoveOverlay() {
    let overlay = document.getElementById('sidebarOverlay');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebar.classList.contains('mobile-open')) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'sidebarOverlay';
            overlay.className = 'sidebar-overlay open';
            document.body.appendChild(overlay);
            
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('mobile-open');
                document.body.classList.remove('sidebar-open');
                overlay.remove();
            });
        } else {
            overlay.classList.add('open');
        }
    } else {
        if (overlay) {
            overlay.classList.remove('open');
            setTimeout(() => overlay.remove(), 240);
        }
    }
}

// ============================================================
// DROPDOWN INTERACTIONS
// ============================================================

function initializeDropdowns() {
    // Notification dropdown
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationDropdown = document.getElementById('notificationDropdown');
    
    if (notificationBtn && notificationDropdown) {
        notificationBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationDropdown.classList.toggle('open');
            // Close user dropdown
            const userDropdown = document.getElementById('userDropdown');
            if (userDropdown) userDropdown.classList.remove('open');
        });
    }

    // User menu dropdown
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            userDropdown.classList.toggle('open');
            // Close notification dropdown
            if (notificationDropdown) notificationDropdown.classList.remove('open');
        });
    }

    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        if (notificationDropdown) notificationDropdown.classList.remove('open');
        if (userDropdown) userDropdown.classList.remove('open');
    });

    // Close dropdowns on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (notificationDropdown) notificationDropdown.classList.remove('open');
            if (userDropdown) userDropdown.classList.remove('open');
        }
    });
}

// ============================================================
// SEARCH INTERACTIONS
// ============================================================

function initializeSearch() {
    const searchInput = document.querySelector('.search-input');
    
    if (!searchInput) return;

    // Command/Ctrl + K to focus search
    document.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
    });

    // Handle search input
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value;
        // Add custom search logic here if needed
        console.log('Search:', query);
    });
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

// Format relative time (e.g., "2 min ago")
function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return new Date(date).toLocaleDateString();
}

// Active nav item based on current route
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && currentPath.includes(href.replace('{{ url_for(\'', '').replace('\') }}', ''))) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

setActiveNavItem();

// Smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && document.querySelector(href)) {
            e.preventDefault();
            document.querySelector(href).scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// ============================================================
// EXPORTS (for use in other modules)
// ============================================================

window.layoutUtils = {
    formatRelativeTime,
    setActiveNavItem,
};
