let slideIndex = 0;
const slides = document.querySelectorAll('.slide');

function showSlide(n) {
    if (!slides.length) return;
    slides.forEach(s => s.classList.remove('active'));
    slideIndex = (n + slides.length) % slides.length;
    slides[slideIndex].classList.add('active');
}

function moveSlide(n) {
    showSlide(slideIndex + n);
}

if (slides.length > 0) {
    setInterval(() => { moveSlide(1); }, 3000);
}