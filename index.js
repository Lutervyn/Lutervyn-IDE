content: function validateLoginForm() {
function validateLoginForm() {
  const username = document.getElementById("loginUsername").value;
    const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;
    const password = document.getElementById("loginPassword").value;
  const errorDiv = document.getElementById("loginError");
    const errorDiv = document.getElementById("loginError");
  errorDiv.textContent = ""; // Clear previous errors
    errorDiv.textContent = ""; // Clear previous errors

  if (!username || !password) {
    if (!username || !password) {
    errorDiv.textContent = "Please fill in all fields.";
        errorDiv.textContent = "Please fill in all fields.";
    return false;
        return false;
  }
    }

  // Add backend integration here
    // Add backend integration here
  // Example:
    // Example:
  // fetch('/login', {
    // fetch('/login', {
  //   method: 'POST',
    //   method: 'POST',
  //   body: JSON.stringify({ username, password }),
    //   body: JSON.stringify({ username, password }),
  //   headers: { 'Content-Type': 'application/json' }
    //   headers: { 'Content-Type': 'application/json' }
  // })
    // })
  // .then(response => response.json())
    // .then(response => response.json())
  // .then(data => {
    // .then(data => {
  //   if (data.success) {
    //   if (data.success) {
  //     window.location.href = '/dashboard';
    //     window.location.href = '/dashboard';
  //   } else {
    //   } else {
  //     errorDiv.textContent = 'Login failed: ' + data.message;
    //     errorDiv.textContent = 'Login failed: ' + data.message;
  //     return false;
    //     return false;
  //   }
    //   }
  // });
    // });

  return true; // Prevent form submission for now. Replace with false if backend validation fails
    return true; // Prevent form submission for now. Replace with false if backend validation fails

}

function validateRegisterForm() {
  const username = document.getElementById("registerUsername").value;
    const username = document.getElementById("registerUsername").value;
  const email = document.getElementById("registerEmail").value;
    const email = document.getElementById("registerEmail").value;
  const password = document.getElementById("registerPassword").value;
    const password = document.getElementById("registerPassword").value;
  const errorDiv = document.getElementById("registerError");
    const errorDiv = document.getElementById("registerError");
  errorDiv.textContent = "";
    errorDiv.textContent = "";

  if (!username || !email || !password) {
    if (!username || !email || !password) {
    errorDiv.textContent = "Please fill in all registration fields.";
        errorDiv.textContent = "Please fill in all registration fields.";
    return false;
        return false;
  }
    }

  // Simple email validation
    // Simple email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    if (!emailRegex.test(email)) {
    errorDiv.textContent = "Please enter a valid email address.";
        errorDiv.textContent = "Please enter a valid email address.";
    return false;
        return false;
  }
    }

  // Password strength validation (example)
  if (password.length < 8) {
    errorDiv.textContent = "Password must be at least 8 characters long.";
    return false;
  }
    // Enhanced password strength validation
    const uppercaseRegex = /[A-Z]/;
    const lowercaseRegex = /[a-z]/;
    const numberRegex = /[0-9]/;
    const symbolRegex = /[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-]/;

  // Add more robust password strength checks here (e.g., requiring numbers, symbols)
    if (password.length < 8) {
        errorDiv.textContent = "Password must be at least 8 characters long.";
        return false;
    } else if (!uppercaseRegex.test(password)) {
        errorDiv.textContent = "Password must contain at least one uppercase letter.";
        return false;
    } else if (!lowercaseRegex.test(password)) {
        errorDiv.textContent = "Password must contain at least one lowercase letter.";
        return false;
    } else if (!numberRegex.test(password)) {
        errorDiv.textContent = "Password must contain at least one number.";
        return false;
    } else if (!symbolRegex.test(password)) {
        errorDiv.textContent = "Password must contain at least one symbol.";
        return false;
    }

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
    return true; // Prevent form submission for now.  Replace with false if backend validation fails
}

// Toggle Functionality
document.addEventListener("DOMContentLoaded", function() {
document.addEventListener("DOMContentLoaded", function () {
  const loginButton = document.getElementById("loginButton");
    const loginButton = document.getElementById("loginButton");
  const registerButton = document.getElementById("registerButton");
    const registerButton = document.getElementById("registerButton");
  const container = document.querySelector(".container");
    const container = document.querySelector(".container");

  loginButton.addEventListener("click", () => {
    loginButton.addEventListener("click", () => {
    container.classList.remove("register-mode");
        container.classList.remove("active");
  });
    });

  registerButton.addEventListener("click", () => {
    registerButton.addEventListener("click", () => {
    container.classList.add("register-mode");
        container.classList.add("active");
  });
    });
    // Initialize password visibility icons
    const loginPasswordInput = document.getElementById("loginPassword");
    const registerPasswordInput = document.getElementById("registerPassword");
    initializePasswordVisibility(loginPasswordInput, 'login');
    initializePasswordVisibility(registerPasswordInput, 'register');

});});
    // File Viewer Functionality
    const openFileButton = document.getElementById("openFileButton");
    const fileEditorDiv = document.getElementById("fileEditor");
    const fileContentTextarea = document.getElementById("fileContent");
    const saveFileButton = document.getElementById("saveFileButton");

    openFileButton.addEventListener("click", () => {
        // Simulate file selection
        const fileContent = "This is the simulated file content.\nYou can edit it here.";
        fileContentTextarea.value = fileContent;
        fileEditorDiv.style.display = "block"; // Show the editor
    });

    saveFileButton.addEventListener("click", () => {
        // Simulate saving the file
        const newContent = fileContentTextarea.value;
        alert("File saved (simulated).\nNew content: " + newContent);
    });
});
function togglePasswordVisibility(inputId, formType) {
    const passwordInput = document.getElementById(inputId);
    const icon = document.querySelector(`#${formType}Form .toggle-password i`);
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
function initializePasswordVisibility(passwordInput, formType) {
    const icon = document.querySelector(`#${formType}Form .toggle-password i`);
    if (passwordInput.type === "password") {
        icon.classList.add("bx-show");
        icon.classList.remove("bx-hide");
    } else {
        icon.classList.add("bx-hide");
        icon.classList.remove("bx-show");
    }
}
function toggleLoginPasswordVisibility() {
    togglePasswordVisibility("loginPassword", "login");
}

function toggleRegisterPasswordVisibility() {
    togglePasswordVisibility("registerPassword", "register");
}