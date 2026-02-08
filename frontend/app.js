// Топ-100 фильмов IMDb (IMDb ID)
const TOP_100_IMDB_IDS = [
    'tt0111161', // The Shawshank Redemption
    'tt0068646', // The Godfather
    'tt0468569', // The Dark Knight
    'tt0071562', // The Godfather Part II
    'tt0050083', // 12 Angry Men
    'tt0108052', // Schindler's List
    'tt0167260', // The Lord of the Rings: The Return of the King
    'tt0110912', // Pulp Fiction
    'tt0120737', // The Lord of the Rings: The Fellowship of the Ring
    'tt0060196', // The Good, the Bad and the Ugly
    'tt0109830', // Forrest Gump
    'tt0137523', // Fight Club
    'tt0167261', // The Lord of the Rings: The Two Towers
    'tt1375666', // Inception
    'tt0080684', // Star Wars: Episode V - The Empire Strikes Back
    'tt0133093', // The Matrix
    'tt0099685', // Goodfellas
    'tt0073486', // One Flew Over the Cuckoo's Nest
    'tt0114369', // Se7en
    'tt0038650', // It's a Wonderful Life
    'tt0102926', // The Silence of the Lambs
    'tt0076759', // Star Wars
    'tt0120815', // Saving Private Ryan
    'tt0317248', // City of God
    'tt0118799', // Life Is Beautiful
    'tt0245429', // Spirited Away
    'tt0047478', // Seven Samurai
    'tt0120689', // The Green Mile
    'tt0816692', // Interstellar
    'tt0114814', // The Usual Suspects
    'tt0103064', // Terminator 2: Judgment Day
    'tt0088763', // Back to the Future
    'tt0054215', // Psycho
    'tt0110413', // Leon: The Professional
    'tt0034583', // Casablanca
    'tt0027977', // Modern Times
    'tt0120586', // American History X
    'tt0021749', // City Lights
    'tt0253474', // The Pianist
    'tt0407887', // The Departed
    'tt0172495', // Gladiator
    'tt0482571', // The Prestige
    'tt0078788', // Apocalypse Now
    'tt0209144', // Memento
    'tt0078748', // Alien
    'tt0032553', // The Great Dictator
    'tt0043014', // Sunset Blvd.
    'tt0082971', // Raiders of the Lost Ark
    'tt0095327', // Grave of the Fireflies
    'tt0057012', // Dr. Strangelove
];

const { createApp, ref, computed, onMounted } = Vue;

createApp({
    setup() {
        // State
        const activeTab = ref('list');
        const listFilter = ref('all');
        const movies = ref([]);
        const loading = ref(false);

        // Search
        const searchQuery = ref('');
        const searchResults = ref([]);
        const searchLoading = ref(false);
        const addingMovie = ref(null);

        // Recommendations
        const recommendQuery = ref('');
        const recommendation = ref(null);
        const recommendLoading = ref(false);

        // Top 100
        const top100Movies = ref([]);
        const top100Loading = ref(false);
        const top100Loaded = ref(false);

        // Notifications
        const notification = ref(null);

        // Computed
        const filteredMovies = computed(() => {
            if (listFilter.value === 'all') {
                return movies.value;
            } else if (listFilter.value === 'watched') {
                return movies.value.filter(m => m.is_watched);
            } else {
                return movies.value.filter(m => !m.is_watched);
            }
        });

        // Methods
        const showNotification = (message, type = 'success') => {
            notification.value = { message, type };
            setTimeout(() => {
                notification.value = null;
            }, 3000);
        };

        const loadMovies = async () => {
            loading.value = true;
            try {
                const response = await fetch('/api/movies');
                movies.value = await response.json();
            } catch (error) {
                showNotification('Ошибка загрузки фильмов', 'error');
            } finally {
                loading.value = false;
            }
        };

        const searchMovies = async () => {
            if (!searchQuery.value.trim()) return;

            searchLoading.value = true;
            searchResults.value = [];
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(searchQuery.value)}`);
                const data = await response.json();
                searchResults.value = data;

                if (data.length === 0) {
                    showNotification('Фильмы не найдены', 'error');
                }
            } catch (error) {
                console.error('Search error:', error);
                showNotification('Ошибка поиска', 'error');
            } finally {
                searchLoading.value = false;
            }
        };

        const addMovie = async (imdbId) => {
            addingMovie.value = imdbId;
            try {
                const response = await fetch('/api/movies', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: imdbId })
                });

                if (response.ok) {
                    const movie = await response.json();
                    movies.value.unshift(movie);
                    showNotification(`«${movie.title}» добавлен в список`);
                    // Убираем из результатов поиска
                    searchResults.value = searchResults.value.filter(r => r.imdb_id !== imdbId);
                } else {
                    const error = await response.json();
                    showNotification(error.detail || 'Ошибка добавления', 'error');
                }
            } catch (error) {
                showNotification('Ошибка добавления фильма', 'error');
            } finally {
                addingMovie.value = null;
            }
        };

        const toggleWatched = async (movie) => {
            try {
                const response = await fetch(`/api/movies/${movie.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_watched: !movie.is_watched })
                });

                if (response.ok) {
                    movie.is_watched = !movie.is_watched;
                    showNotification(
                        movie.is_watched
                            ? `«${movie.title}» отмечен как просмотренный`
                            : `«${movie.title}» возвращён в список к просмотру`
                    );
                }
            } catch (error) {
                showNotification('Ошибка обновления', 'error');
            }
        };

        const deleteMovie = async (movieId) => {
            if (!confirm('Удалить фильм из списка?')) return;

            try {
                const response = await fetch(`/api/movies/${movieId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    movies.value = movies.value.filter(m => m.id !== movieId);
                    showNotification('Фильм удалён');
                }
            } catch (error) {
                showNotification('Ошибка удаления', 'error');
            }
        };

        const getRecommendations = async () => {
            if (!recommendQuery.value.trim()) return;

            recommendLoading.value = true;
            recommendation.value = null;
            try {
                const response = await fetch('/api/recommend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: recommendQuery.value,
                        include_watched: false
                    })
                });

                if (response.ok) {
                    recommendation.value = await response.json();
                } else {
                    showNotification('Ошибка получения рекомендаций', 'error');
                }
            } catch (error) {
                showNotification('Ошибка получения рекомендаций', 'error');
            } finally {
                recommendLoading.value = false;
            }
        };

        const loadTop100 = async () => {
            if (top100Loaded.value) return;

            top100Loading.value = true;
            try {
                // Проверяем, есть ли уже загруженные фильмы топ-100 в базе
                const response = await fetch('/api/movies?source=top100');
                const existingTop100 = await response.json();

                if (existingTop100.length > 0) {
                    // Отмечаем уже добавленные
                    top100Movies.value = existingTop100.map(m => ({ ...m, added: true }));
                    top100Loaded.value = true;
                } else {
                    // Загружаем информацию о топ-50 фильмах из OMDB
                    top100Movies.value = [];
                    top100Loaded.value = true;

                    // Загружаем по 5 фильмов параллельно
                    const batchSize = 5;
                    for (let i = 0; i < TOP_100_IMDB_IDS.length; i += batchSize) {
                        const batch = TOP_100_IMDB_IDS.slice(i, i + batchSize);
                        const promises = batch.map(async (imdbId) => {
                            try {
                                const res = await fetch(`/api/movies/by-imdb/${imdbId}?source=top100`, {
                                    method: 'POST'
                                });
                                if (res.ok) {
                                    return await res.json();
                                }
                            } catch (e) {
                                console.error(`Error loading ${imdbId}:`, e);
                            }
                            return null;
                        });

                        const results = await Promise.all(promises);
                        results.forEach(movie => {
                            if (movie) {
                                top100Movies.value.push({ ...movie, added: true });
                            }
                        });
                    }
                }
            } catch (error) {
                console.error('Top100 error:', error);
                showNotification('Ошибка загрузки топ-100', 'error');
            } finally {
                top100Loading.value = false;
            }
        };

        const addFromTop100 = async (imdbId) => {
            addingMovie.value = imdbId;
            try {
                const response = await fetch(`/api/movies/by-imdb/${imdbId}?source=personal`, {
                    method: 'POST'
                });

                if (response.ok) {
                    const movie = await response.json();
                    // Обновляем карточку в топ-100
                    const idx = top100Movies.value.findIndex(m => m.imdb_id === imdbId);
                    if (idx !== -1) {
                        top100Movies.value[idx] = { ...movie, added: true };
                    }
                    // Добавляем в основной список
                    const existsInMovies = movies.value.find(m => m.imdb_id === imdbId);
                    if (!existsInMovies) {
                        movies.value.unshift(movie);
                    }
                    showNotification(`«${movie.title}» добавлен в список`);
                }
            } catch (error) {
                showNotification('Ошибка добавления', 'error');
            } finally {
                addingMovie.value = null;
            }
        };

        // Lifecycle
        onMounted(() => {
            loadMovies();
        });

        return {
            // State
            activeTab,
            listFilter,
            movies,
            loading,
            searchQuery,
            searchResults,
            searchLoading,
            addingMovie,
            recommendQuery,
            recommendation,
            recommendLoading,
            top100Movies,
            top100Loading,
            notification,

            // Computed
            filteredMovies,

            // Methods
            loadMovies,
            searchMovies,
            addMovie,
            toggleWatched,
            deleteMovie,
            getRecommendations,
            loadTop100,
            addFromTop100
        };
    }
}).mount('#app');
