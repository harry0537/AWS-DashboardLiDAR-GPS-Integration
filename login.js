document.getElementById('login-form').addEventListener('submit', (event) => {
  event.preventDefault(); // Prevent form submission

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;

  // Check credentials
  if (username === 'admin' && password === 'admin') {
    // Save authentication status
    sessionStorage.setItem('authenticated', 'true');
    // Redirect to the dashboard
    window.location.href = 'index.html';
  } else {
    // Show error message
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = 'Invalid username or password. Please try again.';
  }
});