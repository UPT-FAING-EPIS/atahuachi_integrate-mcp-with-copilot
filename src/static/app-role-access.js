document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupTitle = document.getElementById("signup-title");
  const signupDescription = document.getElementById("signup-description");
  const emailLabel = document.getElementById("email-label");
  const signupButton = document.getElementById("signup-button");
  const authButton = document.getElementById("auth-button");
  const logoutButton = document.getElementById("logout-button");
  const roleBadge = document.getElementById("role-badge");
  const authModal = document.getElementById("auth-modal");
  const authForm = document.getElementById("auth-form");
  const closeAuthModalButton = document.getElementById("close-auth-modal");
  const signupContainer = document.getElementById("signup-container");

  let currentUser = {
    authenticated: false,
    username: null,
    displayName: "Student",
    role: "student",
  };

  try {
    const storedUser = window.localStorage.getItem("currentUser");

    if (storedUser) {
      currentUser = {
        ...currentUser,
        ...JSON.parse(storedUser),
      };
    }
  } catch (error) {
    window.localStorage.removeItem("currentUser");
    console.warn("Unable to restore stored user state:", error);
  }

  function saveCurrentUser(user) {
    window.localStorage.setItem("currentUser", JSON.stringify(user));
  }

  function clearCurrentUser() {
    window.localStorage.removeItem("currentUser");
  }

  function isManagementRole(role) {
    return ["organizer", "admin"].includes(role);
  }

  function getCurrentRole() {
    return currentUser.role || "student";
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    window.setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateAuthState() {
    const role = getCurrentRole();
    const isManager = isManagementRole(role);

    roleBadge.textContent = currentUser.authenticated
      ? `${currentUser.displayName} - ${role}`
      : "Student";

    authButton.textContent = currentUser.authenticated ? "Switch teacher" : "Teacher login";
    logoutButton.classList.toggle("hidden", !currentUser.authenticated);

    signupTitle.textContent = isManager ? "Register Student" : "Request Access";
    signupDescription.textContent = isManager
      ? "Teachers can register students directly or approve pending requests from the cards below."
      : "Students request access. Teachers decide whether an activity requires approval.";
    emailLabel.textContent = "Student Email:";
    signupButton.textContent = isManager ? "Register Student" : "Request Access";
    signupContainer.dataset.role = role;
  }

  function openAuthModal() {
    authModal.classList.remove("hidden");
    authModal.setAttribute("aria-hidden", "false");
  }

  function closeAuthModal() {
    authModal.classList.add("hidden");
    authModal.setAttribute("aria-hidden", "true");
  }

  function renderParticipantList(items, activityName, sectionType, isManager) {
    if (items.length === 0) {
      return `<p class="empty-state">No ${sectionType} entries yet.</p>`;
    }

    return `
      <ul class="participants-list ${sectionType}-list">
        ${items
          .map((item) => {
            const actions = [];

            if (isManager && sectionType === "pending") {
              actions.push(
                `<button class="inline-action approve-btn" data-activity="${activityName}" data-email="${item.email}">Approve</button>`,
                `<button class="inline-action reject-btn secondary" data-activity="${activityName}" data-email="${item.email}">Reject</button>`
              );
            }

            if (isManager && sectionType === "approved") {
              actions.push(
                `<button class="inline-action remove-btn secondary" data-activity="${activityName}" data-email="${item.email}">Unregister</button>`
              );
            }

            return `
              <li class="participant-row participant-${item.status}">
                <div class="participant-main">
                  <span class="participant-email">${item.email}</span>
                  <span class="status-pill status-${item.status}">${item.status}</span>
                </div>
                ${actions.length > 0 ? `<div class="row-actions">${actions.join("")}</div>` : ""}
              </li>
            `;
          })
          .join("")}
      </ul>
    `;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const isManager = isManagementRole(getCurrentRole());
        const approvedParticipants = details.participants.filter(
          (participant) => participant.status === "approved"
        );
        const pendingRequests = details.participants.filter(
          (participant) => participant.status === "pending"
        );
        const rejectedRequests = details.participants.filter(
          (participant) => participant.status === "rejected"
        );

        activityCard.innerHTML = `
          <div class="activity-card-header">
            <div>
              <p class="activity-label">${details.requires_approval ? "Approval required" : "Open registration"}</p>
              <h4>${name}</h4>
            </div>
            <span class="status-pill status-open">${details.spots_left} spots left</span>
          </div>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <div class="participants-container">
            <div class="participants-section">
              <h5>Approved</h5>
              ${renderParticipantList(approvedParticipants, name, "approved", isManager)}
            </div>
            <div class="participants-section">
              <h5>Pending</h5>
              ${renderParticipantList(pendingRequests, name, "pending", isManager)}
            </div>
            <div class="participants-section">
              <h5>Rejected</h5>
              ${renderParticipantList(rejectedRequests, name, "rejected", false)}
            </div>
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleActivityAction(event) {
    const button = event.target.closest("button[data-activity]");

    if (!button) {
      return;
    }

    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");
    const role = getCurrentRole();

    let endpoint = "";
    let method = "POST";

    if (button.classList.contains("approve-btn")) {
      endpoint = `/activities/${encodeURIComponent(activity)}/requests/${encodeURIComponent(email)}/approve?role=${encodeURIComponent(role)}`;
    } else if (button.classList.contains("reject-btn")) {
      endpoint = `/activities/${encodeURIComponent(activity)}/requests/${encodeURIComponent(email)}/reject?role=${encodeURIComponent(role)}`;
    } else if (button.classList.contains("remove-btn")) {
      endpoint = `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}&role=${encodeURIComponent(role)}`;
      method = "DELETE";
    }

    if (!endpoint) {
      return;
    }

    try {
      const response = await fetch(endpoint, { method });
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to update registration. Please try again.", "error");
      console.error("Error updating registration:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const activity = document.getElementById("activity").value;
    const role = getCurrentRole();

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}&role=${encodeURIComponent(role)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to update registration. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  authButton.addEventListener("click", openAuthModal);

  logoutButton.addEventListener("click", () => {
    fetch("/auth/logout", { method: "POST" })
      .catch((error) => {
        console.error("Error logging out:", error);
      })
      .finally(() => {
        currentUser = {
          authenticated: false,
          username: null,
          displayName: "Student",
          role: "student",
        };

        clearCurrentUser();
        updateAuthState();
        fetchActivities();
        showMessage("Logged out successfully.", "info");
      });
  });

  closeAuthModalButton.addEventListener("click", closeAuthModal);

  authModal.addEventListener("click", (event) => {
    if (event.target === authModal) {
      closeAuthModal();
    }
  });

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
      const response = await fetch(
        `/auth/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        currentUser = {
          authenticated: true,
          username: result.username,
          displayName: result.display_name,
          role: result.role,
        };

        saveCurrentUser(currentUser);
        updateAuthState();
        closeAuthModal();
        authForm.reset();
        fetchActivities();
        showMessage(`Signed in as ${result.display_name} (${result.role})`, "success");
      } else {
        showMessage(result.detail || "Login failed", "error");
      }
    } catch (error) {
      showMessage("Login failed. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  activitiesList.addEventListener("click", handleActivityAction);

  updateAuthState();
  fetchActivities();
});
