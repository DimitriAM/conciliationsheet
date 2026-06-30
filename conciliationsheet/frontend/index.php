<?php require_once __DIR__ . '/config.php'; ?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conciliation Sheet</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <nav>
        <div class="brand">CS</div>
        <a href="?view=upload" class="<?= ($_GET['view'] ?? 'upload') === 'upload' ? 'active' : '' ?>">Subir</a>
        <a href="?view=dashboard" class="<?= ($_GET['view'] ?? '') === 'dashboard' ? 'active' : '' ?>">Dashboard</a>
        <a href="?view=reports" class="<?= ($_GET['view'] ?? '') === 'reports' ? 'active' : '' ?>">Reportes</a>
        <a href="?view=settings" class="<?= ($_GET['view'] ?? '') === 'settings' ? 'active' : '' ?>">Settings</a>
    </nav>
    <main>
        <?php
        $view = $_GET['view'] ?? 'upload';
        $viewPath = __DIR__ . '/views/' . basename($view) . '.php';
        if (file_exists($viewPath)) {
            include $viewPath;
        } else {
            echo '<div class="card"><p>Vista no encontrada.</p></div>';
        }
        ?>
    </main>

    <div id="toastContainer"></div>
    <script>const API = '<?= API_BASE_URL ?>';</script>
    <script src="js/notify.js"></script>
    <script src="js/upload.js"></script>
    <script src="js/conciliate.js"></script>
    <script src="js/dashboard.js"></script>
    <script src="js/reports.js"></script>
</body>
</html>
