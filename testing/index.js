const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');
function validateLoginForm() {
  const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;
  const errorDiv = document.getElementById("loginError");
  errorDiv.textContent = ""; // Clear previous errors

  if (!username || !password) {
    errorDiv.textContent = "Please fill in all fields.";
    return false;
  }

  // Add backend integration here
  // Example:
  // fetch('/login', {
  //   method: 'POST',
  //   body: JSON.stringify({ username, password }),
  //   headers: { 'Content-Type': 'application/json' }
  // })
  // .then(response => response.json())
  // .then(data => {
  //   if (data.success) {
  //     window.location.href = '/dashboard';
  //   } else {
  //     errorDiv.textContent = 'Login failed: ' + data.message;
  //     return false;
  //   }
  // });

  return true; // Prevent form submission for now. Replace with false if backend validation fails

}

function validateRegisterForm() {
  const username = document.getElementById("registerUsername").value;
  const email = document.getElementById("registerEmail").value;
  const password = document.getElementById("registerPassword").value;
  const errorDiv = document.getElementById("registerError");
  errorDiv.textContent = "";

  if (!username || !email || !password) {
    errorDiv.textContent = "Please fill in all registration fields.";
    return false;
  }

  // Simple email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    errorDiv.textContent = "Please enter a valid email address.";
    return false;
  }

  // Password strength validation (example)
  if (password.length < 8) {
    errorDiv.textContent = "Password must be at least 8 characters long.";
    return false;
  }

  // Add more robust password strength checks here (e.g., requiring numbers, symbols)


  // Add backend integration here
  // Example:
  // fetch('/register', {
  //   method: 'POST',
  //   body: JSON.stringify({ username, email, password }),
  //   headers: { 'Content-Type': 'application/json' }
  // })
  // .then(response => response.json())
  // .then(data => {
  //   if (data.success) {
  //     window.location.href = '/registration-success';
  //   } else {
  //     errorDiv.textContent = 'Registration failed: ' + data.message;
  //     return false;
  //   }
  // });


  return true; // Prevent form submission for now.  Replace with false if backend validation fails
}

// Toggle Functionality
document.addEventListener("DOMContentLoaded", function() {
  const loginButton = document.getElementById("loginButton");
  const registerButton = document.getElementById("registerButton");
  const container = document.querySelector(".container");

  loginButton.addEventListener("click", () => {
    container.classList.remove("active"); // Corrected class name to "active"
  });

registerBtn.addEventListener('click', () => {
  registerButton.addEventListener("click", () => {
  container.classList.add('active');
    container.classList.add("active"); // Corrected class name to "active"
  });
});

loginBtn.addEventListener('click', () => {
  container.classList.remove('active');
});
function toggleLoginPasswordVisibility() {
  const passwordInput = document.getElementById("loginPassword");
  const icon = document.querySelector("#loginForm .toggle-password i");
  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    icon.classList.remove("bx-show");
    icon.classList.add("bx-hide");

  } else {
    passwordInput.type = "password";
    icon.classList.remove("bx-hide");
    icon.classList.add("bx-show");
  }
}

function toggleRegisterPasswordVisibility() {
  const passwordInput = document.getElementById("registerPassword");
  const icon = document.querySelector("#registerForm .toggle-password i");

  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    icon.classList.remove("bx-show");
    icon.classList.add("bx-hide");
  } else {
    passwordInput.type = "password";
    icon.classList.remove("bx-hide");
    icon.classList.add("bx-show");
  }
}