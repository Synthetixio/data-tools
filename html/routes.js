const routes = {
  "/": "https://synthetix.streamlit.app",
  "/all": {
    url: "https://synthetix-all.streamlit.app",
  },
};

function initializeRoute() {
  // Get the path after the domain/repository name
  const path = window.location.pathname.replace("/html", "");

  // Check if it's a special route (like /all)
  const route = routes[path];

  // Handle query parameters
  const params = new URLSearchParams(window.location.search);
  params.set("embedded", "true");

  let finalUrl;
  if (!route) {
    // For any unspecified path, pass it through to the main app
    finalUrl = `https://synthetix.streamlit.app${path}?${params.toString()}`;
  } else if (typeof route === "string") {
    // For root path
    finalUrl = `${route}/?${params.toString()}`;
  } else {
    // For special routes like /all
    finalUrl = `${route.url}/?${params.toString()}`;
  }

  // Set iframe source
  document.getElementById("embeddedFrame").src = finalUrl;
}

// Initialize on page load
window.addEventListener("load", initializeRoute);
