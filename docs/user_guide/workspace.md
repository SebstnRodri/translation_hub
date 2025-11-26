# User Guide: Translation Workspace

The Translation Workspace is the central hub for managing all translation activities within your Frappe instance. It provides a comprehensive dashboard to monitor ongoing jobs, view translation history, and configure the translation service.

## 1. Accessing the Workspace

You can access the workspace by searching for "Translation Workspace" in the Awesome Bar or by navigating to it from the main Desk.

## 2. Dashboard Overview

The workspace dashboard gives you an at-a-glance overview of your translation activities with insightful charts and key metrics.

### Charts

-   **Translations Over Time**: A line chart showing the volume of translation jobs and activity over time.
-   **Monitored Apps Progress**: A bar chart displaying the completion percentage for each app and target language you are monitoring.

### Key Metrics

-   **Total Apps Tracked**: The number of distinct Frappe apps for which translation jobs have been created.
-   **Jobs In Progress**: The number of translation jobs that are currently running.
-   **Jobs Completed (Last 30 Days)**: The count of successful jobs completed within the last month.
-   **Strings Translated (All Time)**: The total number of individual strings translated across all completed jobs.

### Recent Translation Jobs

Below the metrics, you will find a list of the most recent translation jobs. This table provides key information about each job, including its status and progress. You can click on a job title to navigate to the detailed `Translation Job` document.

## 3. Managing Translation Jobs

### Creating a New Job

1.  Click the **"Create New Translation Job"** button in the top-right corner of the workspace.
2.  This will open a new `Translation Job` document.
3.  Fill in the required fields:
    -   **Title**: A descriptive title for your job (e.g., "Translate ERPNext to German").
    -   **Source App**: The Frappe app you want to translate.
    -   **Target Language**: The language you want to translate the app into.
4.  Click **"Save"**.

### Starting a Job

1.  Navigate to the `Translation Job` document you want to run.
2.  If the job's status is `Pending`, `Failed`, or `Cancelled`, you will see a **"Start Job"** button.
3.  Click the **"Start Job"** button.
4.  The job will be enqueued to run in the background. The status will change to `Queued` and then `In Progress`.

### Monitoring a Job

You can monitor the progress of a job directly from its document:

-   **Status**: Shows the current state of the job (`Pending`, `Queued`, `In Progress`, `Completed`, `Failed`).
-   **Progress Percentage**: A visual progress bar showing the completion percentage.
-   **Log**: A detailed log of the translation process, updated in real-time. This is useful for debugging any issues.

## 4. Configuration

You can configure the translation service by navigating to the **Translator Settings** DocType (you can search for it in the Awesome Bar).

### API Settings

-   **API Key**: Your API key for the translation service (e.g., Google Gemini). This is a mandatory field.

### Standardization

-   **Standardization Guide**: You can provide a markdown-formatted guide or glossary here. The AI will use this guide to maintain consistency in terminology and style.

### Automation

The Translation Hub can automatically keep your app translations up-to-date.

1.  **Enable Automated Translation**: Check this box to turn on the scheduler.
2.  **Frequency**: Choose how often the system should check for new translations (`Daily` or `Weekly`).
3.  **Monitored Apps**: In this table, add the `Source App` and `Target Language` combinations you want to monitor.

The system will then periodically check for new or updated strings in the specified apps and automatically create and run translation jobs as needed.
