function handleFormSubmit() {
  const selection = document.getElementById("selection").value;

  let url = "/";
  if (selection === "publications") {
    url += "publications";
  } else if (selection === "citations") {
    url += "citations";
  } else if (selection === "authors") {
    url += "authors";
  }

  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      console.log("Data received:", data);
    })
    .catch((error) => console.error("Error:", error));
}

document
  .getElementById("submitBtn")
  .addEventListener("click", handleFormSubmit);
