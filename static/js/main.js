document.addEventListener('DOMContentLoaded', () => {
    // 🌗 Logik Dwi-Tema (Dark/Light Mode Switcher)
    const themeToggleBtn = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
   
    // Set tema asal semasa loading
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);


    themeToggleBtn.addEventListener('click', () => {
        let theme = document.documentElement.getAttribute('data-theme');
        let newTheme = theme === 'dark' ? 'light' : 'dark';
       
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });


    function updateThemeIcon(theme) {
        themeToggleBtn.innerHTML = theme === 'dark'
            ? '☀️' // Simbol matahari untuk bertukar ke mod terang
            : '🌙'; // Simbol bulan untuk bertukar ke mod gelap
    }


    // ⌨️ Kesan Taip Typewriter Dinamik
    const typewriterElement = document.getElementById('typewriter-text');
    if (typewriterElement) {
        const textToType = typewriterElement.getAttribute('data-text');
        let index = 0;
       
        function typeWriter() {
            if (index < textToType.length) {
                typewriterElement.textContent += textToType.charAt(index);
                index++;
                setTimeout(typeWriter, 50); // Kelajuan menaip (ms)
            }
        }
        // Kosongkan dahulu kandungan teks sebelum ditaip
        typewriterElement.textContent = '';
        typeWriter();
    }
});