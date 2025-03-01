import os
import logging

logger = logging.getLogger('image-similarity')

def ensure_template_files():
    """Make sure template files exist"""
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Define template files to check
    template_files = {
        'admin.html': get_admin_template_content(),
        'logs.html': get_logs_template_content()
    }
    
    # Check and create each template if needed
    for filename, content in template_files.items():
        filepath = os.path.join('templates', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(content)
            logger.info(f"Created template file: {filepath}")

def get_admin_template_content():
    """Return the content for the admin template"""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Image Similarity Explorer Admin</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        button { 
            padding: 10px; 
            margin: 10px 0; 
            cursor: pointer; 
            background-color: #4285F4;
            color: white;
            border: none;
            border-radius: 4px;
        }
        button:hover {
            background-color: #3367D6;
        }
        .card { 
            border: 1px solid #ccc; 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        pre { 
            background: #f5f5f5; 
            padding: 10px; 
            overflow: auto;
            border-radius: 4px;
        }
        .logs-teaser { 
            max-height: 150px; 
            overflow: auto; 
            font-family: monospace; 
            font-size: 12px;
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
        }
        h1 {
            color: #4285F4;
        }
        h2 {
            color: #5F6368;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
    </style>
</head>
<body>
    <h1>Image Similarity Explorer Admin</h1>
    
    <div class="card">
        <h2>Database Management</h2>
        <button id="resetDb">Reset Database & Repopulate</button>
        <button id="fixDb">Fix Database (Remove Missing Images)</button>
        <div id="dbResult"></div>
    </div>
    
    <div class="card">
        <h2>Database/Filesystem Sync</h2>
        <button id="checkSync">Check Sync Status</button>
        <div id="syncResult"></div>
    </div>
    
    <div class="card">
        <h2>Image Directory</h2>
        <button id="listImages">List Available Images</button>
        <div id="imagesResult"></div>
    </div>
    
    <div class="card">
        <h2>Database Status</h2>
        <button id="checkDb">Check Database</button>
        <div id="checkResult"></div>
    </div>
    
    <div class="card">
        <h2>Application Logs</h2>
        <div class="logs-teaser" id="logsTeaser">Loading recent logs...</div>
        <button onclick="window.location.href='/admin/logs'">View All Logs</button>
        <button onclick="refreshLogs()">Refresh</button>
    </div>
    
    <script>
        // Fetch recent logs for the teaser
        async function refreshLogs() {
            try {
                const response = await fetch('/admin/logs?format=json&limit=10');
                const logs = await response.json();
                
                const logsHtml = logs.map(log => 
                    `<div style="${getLogStyle(log.level)}">${log.timestamp} - ${log.level} - ${log.message}</div>`
                ).join('');
                
                document.getElementById('logsTeaser').innerHTML = logsHtml || 'No logs available';
            } catch (error) {
                document.getElementById('logsTeaser').innerHTML = `Error loading logs: ${error.message}`;
            }
        }
        
        function getLogStyle(level) {
            switch(level) {
                case 'ERROR': return 'color: red;';
                case 'WARNING': return 'color: orange;';
                case 'INFO': return 'color: green;';
                default: return '';
            }
        }
        
        document.getElementById('resetDb').addEventListener('click', async () => {
            if (confirm('This will RESET the entire database and rebuild it from the images directory. Continue?')) {
                try {
                    const result = document.getElementById('dbResult');
                    result.innerHTML = 'Processing...';
                    
                    const response = await fetch('/admin/reset-db', { method: 'POST' });
                    const data = await response.json();
                    
                    result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    refreshLogs();
                } catch (error) {
                    document.getElementById('dbResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            }
        });
        
        document.getElementById('fixDb').addEventListener('click', async () => {
            if (confirm('This will remove database nodes for images that don\\'t exist in the filesystem. Continue?')) {
                try {
                    const result = document.getElementById('dbResult');
                    result.innerHTML = 'Processing...';
                    
                    const response = await fetch('/admin/fix-db', { method: 'POST' });
                    const data = await response.json();
                    
                    result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    refreshLogs();
                } catch (error) {
                    document.getElementById('dbResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            }
        });
        
        document.getElementById('checkSync').addEventListener('click', async () => {
            try {
                const result = document.getElementById('syncResult');
                result.innerHTML = 'Loading...';
                
                const response = await fetch('/debug/sync');
                const data = await response.json();
                
                result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (error) {
                document.getElementById('syncResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
            }
        });
        
        document.getElementById('listImages').addEventListener('click', async () => {
            try {
                const result = document.getElementById('imagesResult');
                result.innerHTML = 'Loading...';
                
                const response = await fetch('/debug/images');
                const data = await response.json();
                
                result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (error) {
                document.getElementById('imagesResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
            }
        });
        
        document.getElementById('checkDb').addEventListener('click', async () => {
            try {
                const result = document.getElementById('checkResult');
                result.innerHTML = 'Connecting to database...';
                
                const response = await fetch('/debug/db');
                const data = await response.json();
                
                result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (error) {
                document.getElementById('checkResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
            }
        });
        
        // Initial logs load
        refreshLogs();
    </script>
</body>
</html>"""

def get_logs_template_content():
    """Return the content for the logs template"""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Application Logs</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
        }
        th, td { 
            text-align: left; 
            padding: 8px; 
            border-bottom: 1px solid #ddd; 
        }
        th { 
            background-color: #f2f2f2; 
        }
        tr:hover { 
            background-color: #f5f5f5; 
        }
        .controls { 
            margin-bottom: 20px; 
        }
        button { 
            padding: 8px 12px; 
            margin-right: 10px; 
            background-color: #4285F4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #3367D6;
        }
        h1 {
            color: #4285F4;
        }
        .error {
            color: red;
        }
        .warning {
            color: orange;
        }
        .info {
            color: green;
        }
    </style>
</head>
<body>
    <h1>Application Logs</h1>
    <div class="controls">
        <button onclick="window.location.href='/admin/logs'">All Logs</button>
        <button onclick="window.location.href='/admin/logs?level=ERROR'">Errors Only</button>
        <button onclick="window.location.href='/admin/logs?level=WARNING'">Warnings Only</button>
        <button onclick="window.location.href='/admin/logs?level=INFO'">Info Only</button>
        <button onclick="clearLogs()">Clear Logs</button>
        <button onclick="window.location.href='/admin'">Back to Admin</button>
    </div>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Level</th>
            <th>Message</th>
        </tr>
        {{ logs_html | safe }}
    </table>
    <script>
        function clearLogs() {
            if (confirm('Are you sure you want to clear all logs?')) {
                fetch('/admin/logs/clear', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'ok') {
                            window.location.reload();
                        }
                    });
            }
        }
    </script>
</body>
</html>"""