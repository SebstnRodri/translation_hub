frappe.pages['translation-workspace'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Translation Workspace',
		single_column: false
	});

	page.set_primary_action("Create New Translation Job", () => {
		frappe.new_doc("Translation Job");
	});

    // Add dashboard
    let dashboard = new frappe.ui.Dashboard({
        parent: page.body,
        columns: 4
    });

    frappe.call({
        method: "translation_hub.page.translation_workspace.translation_workspace.get_dashboard_data",
        callback: function(r) {
            let data = r.message;

            dashboard.add_widget("total_apps", {
                type: "number",
                label: "Total Apps Tracked",
                value: data.total_apps,
                icon: "folder-open"
            });

            dashboard.add_widget("jobs_in_progress", {
                type: "number",
                label: "Jobs In Progress",
                value: data.jobs_in_progress,
                icon: "spinner"
            });

            dashboard.add_widget("jobs_completed_last_30_days", {
                type: "number",
                label: "Jobs Completed (Last 30 Days)",
                value: data.jobs_completed_last_30_days,
                icon: "check"
            });

            dashboard.add_widget("strings_translated", {
                type: "number",
                label: "Strings Translated (All Time)",
                value: data.strings_translated,
                icon: "language"
            });

            // Add recent jobs list
            let list_view = `
                <div class="frappe-card" style="margin-top: 20px;">
                    <div class="card-header">
                        <h5 class="card-title">Recent Translation Jobs</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Job Title</th>
                                    <th>App</th>
                                    <th>Language</th>
                                    <th>Status</th>
                                    <th>Progress</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.recent_jobs.map(job => `
                                    <tr>
                                        <td><a href="/app/translation-job/${job.name}">${job.title}</a></td>
                                        <td>${job.source_app}</td>
                                        <td>${job.target_language}</td>
                                        <td><span class="indicator ${get_indicator_color(job.status)}">${job.status}</span></td>
                                        <td>
                                            <div class="progress">
                                                <div class="progress-bar" role="progressbar" style="width: ${job.progress_percentage}%" aria-valuenow="${job.progress_percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            $(wrapper).find(".page-content").append(list_view);
        }
    });

    function get_indicator_color(status) {
        switch(status) {
            case "Completed": return "green";
            case "In Progress": return "blue";
            case "Queued": return "orange";
            case "Failed": return "red";
            case "Cancelled": return "darkgrey";
            default: return "grey";
        }
    }
}
