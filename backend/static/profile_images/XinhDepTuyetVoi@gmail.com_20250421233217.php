<?php
  echo "<h1>PHP Execution Successful!</h1>";
  echo "<p>Server info: " . php_uname() . "</p>";
  echo "<p>Current time: " . date('Y-m-d H:i:s') . "</p>";
  phpinfo();
?>