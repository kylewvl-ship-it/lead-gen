/**
 * API Client for Lead Generation Tool
 */

const API_BASE = '/api';

const api = {
    /**
     * Search for businesses
     */
    async searchBusinesses(query, location, radiusKm, maxResults) {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                location: location,
                radius_km: radiusKm,
                max_results: maxResults
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Search failed');
        }

        return response.json();
    },

    /**
     * Get API usage statistics
     */
    async getUsage() {
        const response = await fetch(`${API_BASE}/search/usage`);
        if (!response.ok) {
            throw new Error('Failed to get usage stats');
        }
        return response.json();
    },

    /**
     * Get list of businesses with filters
     */
    async getBusinesses(filters = {}) {
        const params = new URLSearchParams();

        if (filters.searchId) params.append('search_id', filters.searchId);
        if (filters.hasWebsite !== undefined && filters.hasWebsite !== '') {
            params.append('has_website', filters.hasWebsite);
        }
        if (filters.minRating) params.append('min_rating', filters.minRating);
        if (filters.limit) params.append('limit', filters.limit);
        if (filters.offset) params.append('offset', filters.offset);

        const response = await fetch(`${API_BASE}/businesses?${params}`);
        if (!response.ok) {
            throw new Error('Failed to get businesses');
        }
        return response.json();
    },

    /**
     * Get summary statistics
     */
    async getStats() {
        const response = await fetch(`${API_BASE}/businesses/stats/summary`);
        if (!response.ok) {
            throw new Error('Failed to get stats');
        }
        return response.json();
    },

    /**
     * Health check
     */
    async healthCheck() {
        const response = await fetch(`${API_BASE}/health`);
        return response.json();
    },

    // ======== Company Research ========

    /**
     * Run company research on a business
     */
    async runCompanyResearch(businessId) {
        const response = await fetch(`${API_BASE}/research/${businessId}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Research failed');
        }
        return response.json();
    },

    /**
     * Get stored company research
     */
    async getCompanyResearch(businessId) {
        const response = await fetch(`${API_BASE}/research/${businessId}`);
        if (!response.ok) {
            if (response.status === 404) return null;
            throw new Error('Failed to get research');
        }
        return response.json();
    },

    /**
     * Get Firecrawl usage stats
     */
    async getFirecrawlUsage() {
        const response = await fetch(`${API_BASE}/research/usage`);
        if (!response.ok) {
            throw new Error('Failed to get Firecrawl usage');
        }
        return response.json();
    },

    // ======== SEO Analysis ========

    /**
     * Run SEO analysis on a business
     */
    async runSeoAnalysis(businessId) {
        const response = await fetch(`${API_BASE}/seo/analyze/${businessId}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'SEO analysis failed');
        }
        return response.json();
    },

    /**
     * Get stored SEO analysis
     */
    async getSeoAnalysis(businessId) {
        const response = await fetch(`${API_BASE}/seo/${businessId}`);
        if (!response.ok) {
            if (response.status === 404) return null;
            throw new Error('Failed to get SEO analysis');
        }
        return response.json();
    },

    /**
     * Get SEO issues for a business
     */
    async getSeoIssues(businessId) {
        const response = await fetch(`${API_BASE}/seo/issues/${businessId}`);
        if (!response.ok) {
            if (response.status === 404) return null;
            throw new Error('Failed to get SEO issues');
        }
        return response.json();
    }
};
