document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('recommendForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const resultsSection = document.getElementById('resultsSection');
    const resultsList = document.getElementById('resultsList');
    const metaInfo = document.getElementById('metaInfo');
    const fallbackWarning = document.getElementById('fallbackWarning');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI Loading state
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        fallbackWarning.classList.add('hidden');
        
        const formData = new FormData(form);
        const requestData = {
            location: formData.get('location') || null,
            budget: formData.get('budget') || null,
            cuisines: formData.get('cuisines') || null,
            min_rating: formData.get('min_rating') || null,
            free_text: formData.get('free_text') || null,
        };

        try {
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to fetch recommendations');
            }

            const data = await response.json();
            renderResults(data);
        } catch (error) {
            console.error('Error:', error);
            alert(`Error: ${error.message}`);
        } finally {
            // Restore UI state
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });

    function renderResults(data) {
        resultsList.innerHTML = '';
        
        // Show meta info
        const usedLlm = data.used_llm;
        let metaHtml = `Filtered <strong>${data.candidate_count}</strong> candidates out of ${data.total_restaurants} total.`;
        if (data.relaxations_applied && data.relaxations_applied.length > 0) {
            metaHtml += `<br><span style="color: #ffaa00">Relaxed filters: ${data.relaxations_applied.join(', ')}</span>`;
        }
        metaInfo.innerHTML = metaHtml;

        // Show fallback warning if LLM failed
        if (!usedLlm && data.top.length > 0) {
            fallbackWarning.classList.remove('hidden');
        }

        if (data.top.length === 0) {
            resultsList.innerHTML = `
                <div class="restaurant-card" style="text-align: center; color: var(--text-muted)">
                    <h3>No matches found.</h3>
                    <p>Try relaxing your constraints.</p>
                </div>
            `;
            resultsSection.classList.remove('hidden');
            return;
        }

        data.top.forEach((item, index) => {
            const r = item; 
            const rating = r.rating ? Number(r.rating).toFixed(1) : 'N/A';
            const cost = r.cost_for_two ? \`₹\${r.cost_for_two}\` : 'N/A';
            
            // Format cuisines
            let cuisinesHtml = '';
            if (r.cuisines && r.cuisines.length > 0) {
                cuisinesHtml = r.cuisines.map(c => \`<span class="tag">\${c}</span>\`).join('');
            }
            
            const tagCost = \`<span class="tag">Cost: \${cost}</span>\`;
            
            const card = document.createElement('div');
            card.className = 'restaurant-card';
            card.style.animationDelay = \`\${index * 0.1}s\`;
            card.style.animation = \`slideUp 0.5s ease forwards \${index * 0.1}s\`;
            card.style.opacity = '0'; // hide initially for animation
            
            card.innerHTML = \`
                <div class="card-header">
                    <div>
                        <div class="res-name">\${index + 1}. \${r.name}</div>
                        <div class="res-location">\${r.location || 'Unknown location'}</div>
                    </div>
                    <div class="res-rating">
                        ★ \${rating}
                    </div>
                </div>
                <div class="res-tags">
                    \${tagCost}
                    \${cuisinesHtml}
                </div>
                <div class="res-explanation">
                    <strong>Why this fits:</strong> \${r.explanation}
                </div>
            \`;
            
            resultsList.appendChild(card);
        });

        resultsSection.classList.remove('hidden');
        // Small delay to ensure render is complete before scrolling
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 50);
    }
});
