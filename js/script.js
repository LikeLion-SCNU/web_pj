// ===================================
// Mobile Navigation Toggle
// ===================================
const hamburger = document.querySelector('.hamburger');
const navMenu = document.querySelector('.nav-menu');

hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navMenu.classList.toggle('active');
});

// Close mobile menu when clicking on a link
document.querySelectorAll('.nav-menu li a').forEach(link => {
    link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
    });
});

// ===================================
// Smooth Scroll & Active Navigation
// ===================================
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-menu li a');

function updateActiveNav() {
    const scrollY = window.pageYOffset;

    sections.forEach(section => {
        const sectionHeight = section.offsetHeight;
        const sectionTop = section.offsetTop - 100;
        const sectionId = section.getAttribute('id');

        if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${sectionId}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}

window.addEventListener('scroll', updateActiveNav);

// ===================================
// Header Scroll Effect
// ===================================
const header = document.querySelector('.header');

function handleScroll() {
    if (window.scrollY > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
}

window.addEventListener('scroll', handleScroll);

// ===================================
// Team Tabs Functionality
// ===================================
const teamTabs = document.querySelectorAll('.team-tab');
const teamContents = document.querySelectorAll('.team-content');

teamTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const generation = tab.getAttribute('data-generation');

        // Remove active class from all tabs and contents
        teamTabs.forEach(t => t.classList.remove('active'));
        teamContents.forEach(c => c.classList.remove('active'));

        // Add active class to clicked tab and corresponding content
        tab.classList.add('active');
        document.querySelector(`.team-content[data-generation="${generation}"]`).classList.add('active');
    });
});

// ===================================
// Section Transition Animation
// ===================================
const sectionObserverOptions = {
    threshold: 0.15,
    rootMargin: '0px 0px -100px 0px'
};

const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, sectionObserverOptions);

// Observe all sections
const allSections = document.querySelectorAll('.section');
allSections.forEach(section => {
    sectionObserver.observe(section);
});

// ===================================
// Scroll Animation (Fade In on Scroll)
// ===================================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
            setTimeout(() => {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }, index * 100); // Stagger animation
        }
    });
}, observerOptions);

// Apply animation to cards
const animatedElements = document.querySelectorAll(
    '.feature-card, .activity-card, .member-card, .info-card, .cta-box, .contact-info'
);

animatedElements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// ===================================
// Parallax Effect for Hero
// ===================================
const heroContent = document.querySelector('.hero-content');

window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    if (heroContent && scrolled < 800) {
        heroContent.style.transform = `translateY(${scrolled * 0.3}px)`;
        heroContent.style.opacity = `${1 - scrolled / 800}`;
    }
});

// ===================================
// Current Year in Footer
// ===================================
const currentYear = new Date().getFullYear();
const footerYear = document.querySelector('.footer-bottom p');
if (footerYear) {
    footerYear.textContent = `© ${currentYear} LIKELION SUNCHON. All rights reserved.`;
}

// ===================================
// Recruitment Status Check
// ===================================
// Recruitment Status Check
function checkRecruitmentStatus() {
    // 아기사자 모집 기간: 2026-02-19 ~ 2026-03-06
    // Date(year, monthIndex, day, hours, minutes, seconds) - Month is 0-indexed (0=Jan, 1=Feb, 2=Mar...)
    const recruitmentStart = new Date(2026, 1, 19, 0, 0, 0); // 2월 19일 00:00:00
    const recruitmentEnd = new Date(2026, 2, 6, 23, 59, 59); // 3월 6일 23:59:59
    const today = new Date();

    const applyButton = document.querySelector('.apply-button');

    // 날짜 비교
    console.log("Today:", today);
    console.log("Start:", recruitmentStart);
    console.log("End:", recruitmentEnd);

    if (today < recruitmentStart) { // 현재가 시작일보다 전이면 (아직 안됨)
        console.log("Status: Scheduled");
        applyButton.textContent = '모집 예정';
        applyButton.style.pointerEvents = 'none';
        applyButton.style.opacity = '0.6';
    } else if (today > recruitmentEnd) { // 현재가 마감일보다 후면 (끝남)
        console.log("Status: Closed");
        applyButton.textContent = '모집 마감';
        applyButton.style.pointerEvents = 'none';
        applyButton.style.opacity = '0.6';
    } else { // 기간 내 (열림)
        console.log("Status: Open");
        // 모집 중일 때는 HTML에 적힌 텍스트와 링크를 그대로 유지합니다.
        applyButton.style.pointerEvents = 'auto';
        applyButton.style.opacity = '1';
        // 강제로 텍스트와 링크 주입 (안전장치)
        applyButton.textContent = '아기사자 지원서 작성하기';
        applyButton.href = 'https://docs.google.com/forms/d/e/1FAIpQLSeXF2Z-dCpGoSQnxft5VOzbQcDrNMuJWqvTsuLsXa07nDJOUQ/viewform?usp=dialog';
    }
}

checkRecruitmentStatus();

// ===================================
// Smooth Scroll for CTA Buttons
// ===================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');

        // Skip if it's just a placeholder #
        if (href === '#') {
            e.preventDefault();
            return;
        }

        const target = document.querySelector(href);
        if (target) {
            e.preventDefault();
            const headerOffset = 80;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// ===================================
// Loading Animation
// ===================================
window.addEventListener('load', () => {
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});

// ===================================
// Prevent Empty Image Alt Text Issues
// ===================================
document.querySelectorAll('img').forEach(img => {
    img.addEventListener('error', function () {
        this.style.display = 'none';
        if (this.parentElement.classList.contains('activity-image') ||
            this.parentElement.classList.contains('member-image')) {
            this.parentElement.classList.add('placeholder');
        }
    });
});

// ===================================
// Console Welcome Message
// ===================================
console.log('%c순천대학교 멋쟁이사자처럼', 'color: #FF7710; font-size: 24px; font-weight: bold;');
console.log('%c코딩으로 세상을 변화시키는 대학생 IT 창업 동아리', 'color: #666; font-size: 14px;');
console.log('%cWebsite developed with ❤️ by LIKELION SUNCHON', 'color: #999; font-size: 12px;');
