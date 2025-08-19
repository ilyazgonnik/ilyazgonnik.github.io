// Конфигурация жанров
const GENRES = {
    comedy: { name: "Комедия", emoji: "😂" },
    horror: { name: "Ужасы", emoji: "👻" },
    drama: { name: "Драма", emoji: "🎭" },
    sci_fi: { name: "Фантастика", emoji: "🚀" },
    action: { name: "Боевик", emoji: "💥" }
};

let enabledGenres = [];
let isChatInitialized = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeGenreToggles();
    setupEventListeners();
});

function initializeGenreToggles() {
    const container = document.getElementById('genreToggles');
    
    for (const [key, genre] of Object.entries(GENRES)) {
        const label = document.createElement('label');
        label.className = 'toggle-label';
        label.innerHTML = `
            <input type="checkbox" value="${key}">
            <span class="toggle-slider"></span>
            ${genre.emoji} ${genre.name}
        `;
        container.appendChild(label);
    }
}

function setupEventListeners() {
    // Обработчики для чекбоксов
    document.querySelectorAll('.toggle-label input').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedGenres);
    });
    
    // Кнопка начала чата
    document.getElementById('startChatBtn').addEventListener('click', startChat);
    
    // Кнопка сброса
    document.getElementById('resetChatBtn').addEventListener('click', resetChat);
    
    // Отправка сообщения
    document.getElementById('sendMessageBtn').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
}

function updateSelectedGenres() {
    enabledGenres = Array.from(document.querySelectorAll('.toggle-label input:checked'))
        .map(checkbox => checkbox.value);
    
    const countElement = document.getElementById('selectedCount');
    const startButton = document.getElementById('startChatBtn');
    
    countElement.textContent = enabledGenres.length;
    startButton.disabled = enabledGenres.length === 0;
}

async function startChat() {
    if (enabledGenres.length === 0) {
        alert('Пожалуйста, выберите хотя бы один жанр!');
        return;
    }
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/chat/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                enabled_genres: enabledGenres
            })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка инициализации чата');
        }
        
        const data = await response.json();
        
        // Показываем чат
        document.getElementById('chatContainer').style.display = 'block';
        document.getElementById('messageInput').disabled = false;
        document.getElementById('sendMessageBtn').disabled = false;
        
        // Блокируем выбор жанров
        document.querySelectorAll('.toggle-label input').forEach(checkbox => {
            checkbox.disabled = true;
        });
        
        isChatInitialized = true;
        
        // Добавляем системное сообщение
        addMessage('system', `Чат начат с жанрами: ${enabledGenres.map(g => GENRES[g].name).join(', ')}`);
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при запуске чата. Попробуйте еще раз.');
    }
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || !isChatInitialized) return;
    
    // Добавляем сообщение пользователя
    addMessage('user', message);
    input.value = '';
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                enabled_genres: enabledGenres,
                messages: [{ role: 'user', content: message }]
            })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка отправки сообщения');
        }
        
        const data = await response.json();
        addMessage('assistant', data.response);
        
    } catch (error) {
        console.error('Ошибка:', error);
        addMessage('system', '❌ Ошибка соединения с сервером');
    }
}

function addMessage(role, content) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.textContent = content;
    messagesContainer.appendChild(messageDiv);
    
    // Прокрутка вниз
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function resetChat() {
    // Сбрасываем состояние
    enabledGenres = [];
    isChatInitialized = false;
    
    // Сбрасываем чекбоксы
    document.querySelectorAll('.toggle-label input').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.disabled = false;
    });
    
    // Обновляем счетчик
    document.getElementById('selectedCount').textContent = '0';
    document.getElementById('startChatBtn').disabled = true;
    
    // Скрываем чат
    document.getElementById('chatContainer').style.display = 'none';
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendMessageBtn').disabled = true;
    
    // Очищаем сообщения
    document.getElementById('chatMessages').innerHTML = '';
}