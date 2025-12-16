// Ensure namespace exists
window.translation_hub = window.translation_hub || {};

frappe.pages['review-center'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Review Center'),
        single_column: true
    });

    new translation_hub.ReviewCenter(page);
}

translation_hub.ReviewCenter = class ReviewCenter {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.reviews = [];
        this.selected_review = null;

        // Check for URL parameter early
        const urlParams = new URLSearchParams(window.location.search);
        this.requested_review = urlParams.get('review');

        this.setup_page();
        this.make_filters();
        this.make_ui();
        this.load_reviews();
    }

    setup_page() {
        // Primary Action
        this.page.set_primary_action(__('Refresh'), () => this.load_reviews(), 'refresh');

        // Secondary Action - Go to full list
        this.page.add_inner_button(__('View Full List'), () => {
            frappe.set_route('List', 'Translation Review');
        });
    }

    make_filters() {
        this.source_app_filter = this.page.add_field({
            fieldname: 'source_app',
            label: __('App'),
            fieldtype: 'Link',
            options: 'Installed App',
            change: () => this.load_reviews()
        });

        this.language_filter = this.page.add_field({
            fieldname: 'language',
            label: __('Language'),
            fieldtype: 'Link',
            options: 'Language',
            default: 'pt-BR',
            change: () => this.load_reviews()
        });
    }

    make_ui() {
        this.wrapper.html(`
            <div class="review-center-container">
                <div class="review-list-panel">
                    <div class="list-header">
                        <span class="text-muted">${__('Pending Reviews')}</span>
                        <span class="review-count badge badge-secondary">0</span>
                    </div>
                    <div class="review-list"></div>
                </div>
                <div class="review-detail-panel">
                    <div class="empty-detail">
                        <div class="empty-icon">📋</div>
                        <p class="text-muted">${__('Select a review from the list')}</p>
                    </div>
                    <div class="detail-content hidden">
                        <div class="detail-header">
                            <div class="detail-badges"></div>
                            <button class="btn btn-xs btn-default btn-close-detail">✕</button>
                        </div>
                        <div class="detail-body">
                            <div class="form-group">
                                <label class="control-label">${__('Source Text')}</label>
                                <div class="source-text-display"></div>
                            </div>
                            <div class="form-group">
                                <label class="control-label">${__('Current Translation')}</label>
                                <div class="current-text-display text-muted"></div>
                            </div>
                            <div class="form-group">
                                <label class="control-label">${__('Suggested Translation')}</label>
                                <textarea class="form-control translation-input" rows="4"></textarea>
                            </div>
                            <div class="ai-diff hidden">
                                <small class="text-warning"><strong>${__('AI Original:')}</strong></small>
                                <div class="ai-original-text text-muted small"></div>
                            </div>
                        </div>
                        <div class="detail-actions">
                            <button class="btn btn-danger btn-sm btn-reject">
                                <span class="icon">✕</span> ${__('Reject')}
                            </button>
                            <button class="btn btn-success btn-sm btn-approve">
                                <span class="icon">✓</span> ${__('Approve')}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);

        this.bind_events();
    }

    bind_events() {
        // Close detail panel
        this.wrapper.find('.btn-close-detail').on('click', () => {
            this.close_detail();
        });

        // Approve
        this.wrapper.find('.btn-approve').on('click', () => this.approve());

        // Reject
        this.wrapper.find('.btn-reject').on('click', () => this.reject());

        // Keyboard shortcuts
        $(document).on('keydown', (e) => {
            if (!this.selected_review) return;
            if ($(e.target).is('input, textarea')) return;

            if (e.key === 'a' || e.key === 'A') {
                e.preventDefault();
                this.approve();
            }
            if (e.key === 'r' || e.key === 'R') {
                e.preventDefault();
                this.reject();
            }
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.select_next();
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.select_prev();
            }
        });
    }

    load_reviews() {
        const filters = {
            source_app: this.source_app_filter.get_value(),
            language: this.language_filter.get_value() || 'pt-BR',
            status: 'Pending'
        };

        this.wrapper.find('.review-list').html(`
            <div class="text-center p-4 text-muted">
                <span class="spinner-border spinner-border-sm"></span> ${__('Loading...')}
            </div>
        `);

        frappe.call({
            method: 'translation_hub.api.review_api.get_reviews',
            args: filters,
            callback: (r) => {
                this.reviews = r.message || [];

                // Use cached URL parameter from constructor
                const reviewName = this.requested_review;

                // Render list - skip auto-select if URL parameter exists
                this.render_list(!!reviewName);

                if (reviewName) {
                    // Clear cached value to prevent re-triggering
                    this.requested_review = null;

                    // Find and select the requested review
                    const index = this.reviews.findIndex(rev => rev.name === reviewName);
                    if (index >= 0) {
                        this.select_review(index);
                    } else {
                        // Review not in current filters, try to load it directly
                        this.load_specific_review(reviewName);
                    }
                    // Clear URL parameter to avoid re-selecting on refresh
                    window.history.replaceState({}, '', '/desk/review-center');
                }
            },
            error: () => {
                this.wrapper.find('.review-list').html(`
                    <div class="text-center p-4 text-danger">
                        ${__('Failed to load reviews')}
                    </div>
                `);
            }
        });
    }

    load_specific_review(reviewName) {
        // Load a specific review even if it's not in current filter
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Translation Review',
                name: reviewName
            },
            callback: (r) => {
                if (r.message) {
                    if (r.message.status === 'Pending') {
                        // Add to reviews array and select it
                        this.reviews.unshift(r.message);
                        this.render_list(true);  // Skip auto-select, we'll select manually
                        this.select_review(0);

                        // Update filters to match this review
                        if (r.message.source_app) {
                            this.source_app_filter.set_value(r.message.source_app);
                        }
                        if (r.message.language) {
                            this.language_filter.set_value(r.message.language);
                        }
                    } else {
                        // Review is not pending (already approved/rejected)
                        frappe.msgprint({
                            title: __('Review Already Processed'),
                            indicator: r.message.status === 'Approved' ? 'green' : 'red',
                            message: __('This review ({0}) has already been {1}. <a href="/desk/Form/Translation Review/{2}">View it here</a>.',
                                [reviewName, r.message.status, reviewName])
                        });
                    }
                }
            },
            error: () => {
                frappe.msgprint({
                    title: __('Review Not Found'),
                    indicator: 'red',
                    message: __('Could not find review: {0}', [reviewName])
                });
            }
        });
    }

    render_list(skipAutoSelect = false) {
        const $list = this.wrapper.find('.review-list');
        this.wrapper.find('.review-count').text(this.reviews.length);

        if (this.reviews.length === 0) {
            $list.html(`
                <div class="empty-list">
                    <div class="empty-icon">🎉</div>
                    <p>${__('All caught up!')}</p>
                    <small class="text-muted">${__('No pending reviews')}</small>
                </div>
            `);
            return;
        }

        let html = '';
        this.reviews.forEach((review, index) => {
            const source_preview = (review.source_text || '').substring(0, 60);
            html += `
                <div class="review-item" data-index="${index}" data-name="${review.name}">
                    <div class="item-source">${frappe.utils.escape_html(source_preview)}${source_preview.length >= 60 ? '...' : ''}</div>
                    <div class="item-meta">
                        <span class="badge badge-light">${review.source_app || '-'}</span>
                    </div>
                </div>
            `;
        });

        $list.html(html);

        // Bind click
        $list.find('.review-item').on('click', (e) => {
            const index = $(e.currentTarget).data('index');
            this.select_review(index);
        });

        // Auto-select first (unless skipAutoSelect is true)
        if (this.reviews.length > 0 && !skipAutoSelect) {
            this.select_review(0);
        }
    }

    select_review(index) {
        if (index < 0 || index >= this.reviews.length) return;

        this.selected_index = index;
        this.selected_review = this.reviews[index];

        // Update list selection
        this.wrapper.find('.review-item').removeClass('selected');
        this.wrapper.find(`.review-item[data-index="${index}"]`).addClass('selected');

        // Show detail
        this.show_detail(this.selected_review);
    }

    select_next() {
        if (this.selected_index < this.reviews.length - 1) {
            this.select_review(this.selected_index + 1);
        }
    }

    select_prev() {
        if (this.selected_index > 0) {
            this.select_review(this.selected_index - 1);
        }
    }

    show_detail(review) {
        this.wrapper.find('.empty-detail').addClass('hidden');
        this.wrapper.find('.detail-content').removeClass('hidden');

        // Badges
        this.wrapper.find('.detail-badges').html(`
            <span class="badge badge-primary">${review.source_app || '-'}</span>
            <span class="badge badge-secondary">${review.language || '-'}</span>
        `);

        // Content
        this.wrapper.find('.source-text-display').text(review.source_text || '-');
        this.wrapper.find('.current-text-display').text(review.translated_text || __('(no current translation)'));
        this.wrapper.find('.translation-input').val(review.suggested_text || '');

        // AI diff
        if (review.ai_suggestion_snapshot && review.ai_suggestion_snapshot !== review.suggested_text) {
            this.wrapper.find('.ai-diff').removeClass('hidden');
            this.wrapper.find('.ai-original-text').text(review.ai_suggestion_snapshot);
        } else {
            this.wrapper.find('.ai-diff').addClass('hidden');
        }

        // Focus input
        this.wrapper.find('.translation-input').focus();
    }

    close_detail() {
        this.selected_review = null;
        this.selected_index = -1;
        this.wrapper.find('.review-item').removeClass('selected');
        this.wrapper.find('.detail-content').addClass('hidden');
        this.wrapper.find('.empty-detail').removeClass('hidden');
    }

    approve() {
        if (!this.selected_review) return;

        const adjusted_text = this.wrapper.find('.translation-input').val();

        frappe.call({
            method: 'translation_hub.api.review_api.process_review',
            args: {
                name: this.selected_review.name,
                action: 'Approve',
                adjusted_text: adjusted_text
            },
            freeze: true,
            callback: (r) => {
                if (!r.exc) {
                    frappe.show_alert({ message: __('Approved!'), indicator: 'green' }, 2);
                    this.remove_current_and_next();
                }
            }
        });
    }

    reject() {
        if (!this.selected_review) return;

        frappe.prompt([
            {
                label: __('Rejection Reason'),
                fieldname: 'reason',
                fieldtype: 'Small Text',
                reqd: 1,
                description: __('Why is this translation incorrect?')
            },
            {
                fieldtype: 'Section Break',
                label: __('Term Correction (Optional)'),
                description: __('If a specific term is consistently mistranslated, fill in below to teach the AI.')
            },
            {
                label: __('Problematic Term (Original)'),
                fieldname: 'problematic_term',
                fieldtype: 'Data',
                description: __('e.g. "against"')
            },
            {
                label: __('Correct Translation'),
                fieldname: 'correct_term',
                fieldtype: 'Data',
                description: __('e.g. "para" (not "contra")')
            }
        ], (values) => {
            frappe.call({
                method: 'translation_hub.api.review_api.process_review',
                args: {
                    name: this.selected_review.name,
                    action: 'Reject',
                    reason: values.reason,
                    problematic_term: values.problematic_term || null,
                    correct_term: values.correct_term || null
                },
                freeze: true,
                callback: (r) => {
                    if (!r.exc) {
                        let msg = __('Rejected');
                        if (values.problematic_term && values.correct_term) {
                            msg += ' - ' + __('Term learning saved!');
                        }
                        frappe.show_alert({ message: msg, indicator: 'orange' }, 3);
                        this.remove_current_and_next();
                    }
                }
            });
        }, __('Reject Translation'), __('Confirm'));
    }

    remove_current_and_next() {
        // Remove from array
        this.reviews.splice(this.selected_index, 1);

        // Re-render
        this.render_list();

        // Select next (or previous if at end)
        if (this.reviews.length > 0) {
            const nextIndex = Math.min(this.selected_index, this.reviews.length - 1);
            this.select_review(nextIndex);
        } else {
            this.close_detail();
        }
    }
};
