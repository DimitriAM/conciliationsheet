<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($uri === '/') {
    require __DIR__ . '/index.php';
    return true;
}

$file = __DIR__ . $uri;
if (file_exists($file) && is_file($file)) {
    return false;
}

http_response_code(404);
echo "404 - Not Found: $uri";
return true;
