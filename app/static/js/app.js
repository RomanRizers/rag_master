document.getElementById('searchButton').addEventListener('click', async () => {
    const query = document.getElementById('query').value.trim();
    const top_k = document.getElementById('top_k').value.trim() || 5;

    if (!query) {
        alert("Please enter a query.");
        return;
    }

    try {
        const response = await fetch('/searching', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query, top_k: parseInt(top_k) }),
        });

        const data = await response.json();

        const resultsContainer = document.getElementById('results');
        clearElement(resultsContainer);

        if (response.ok && data.results.length > 0) {
            data.results.forEach(result => {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'result';

                const payload = result.payload || {};
                appendResultLine(resultDiv, 'Score', String(result.score ?? 'N/A'));
                appendResultLine(resultDiv, 'Контент', payload.content || 'No content available');
                appendResultLine(
                    resultDiv,
                    'Ключевые слова',
                    Array.isArray(payload.keywords) && payload.keywords.length > 0
                        ? payload.keywords.join(', ')
                        : 'No keywords available'
                );

                resultsContainer.appendChild(resultDiv);
            });
        } else {
            const noResults = document.createElement('p');
            noResults.textContent = 'No results found.';
            resultsContainer.appendChild(noResults);
        }
        
    } catch (error) {
        console.error("Error fetching search results:", error);
        alert("An error occurred while searching. Please check the console for details.");
    }
});

function clearElement(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

function appendResultLine(container, label, value) {
    const paragraph = document.createElement('p');
    const strong = document.createElement('strong');
    strong.textContent = `${label}:`;
    paragraph.appendChild(strong);
    paragraph.appendChild(document.createTextNode(` ${value}`));
    container.appendChild(paragraph);
}

const tooltip = document.getElementById('tooltipTopK');
const inputTopK = document.getElementById('top_k');

inputTopK.addEventListener('mousemove', function (e) {
    tooltip.style.left = e.pageX + 10 + 'px';
    tooltip.style.top = e.pageY + 10 + 'px';  
});

inputTopK.addEventListener('mouseenter', function () {
    tooltip.style.display = 'block';
});

inputTopK.addEventListener('mouseleave', function () {
    tooltip.style.display = 'none'; 
});

// Переводы
const translations = {
    en: {
        title: "Paragraph Search Service",
        tooltip: "Enter the number of results to display, default is 5.",
        query: "Enter your query",
        button: "Search"
    },
    ru: {
        title: "Сервис поиска параграфов",
        tooltip: "Введите количество результатов для вывода, по умолчанию 5.",
        query: "Введите запрос",
        button: "Искать"
    }
};


function setLanguage(language) {
    localStorage.setItem("language", language);

    const elements = document.querySelectorAll("[data-translate]");
    elements.forEach(element => {
        const key = element.getAttribute("data-translate");
        if (translations[language][key]) {
            element.textContent = translations[language][key];
        }
    });
    const placeholders = document.querySelectorAll("[data-translate-query]");
    placeholders.forEach(element => {
    const key = element.getAttribute("data-translate-query");
    if (translations[language][key]) {
        element.setAttribute("placeholder", translations[language][key]);
    }
});

    document.querySelectorAll(".language a").forEach(link => {
        link.classList.remove("active");
    });
    document.getElementById(`lang-${language}`).classList.add("active");
}

const savedLanguage = localStorage.getItem("language") || "ru";
setLanguage(savedLanguage);
