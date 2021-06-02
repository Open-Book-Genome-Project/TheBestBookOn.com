var base_url = '//' + window.location.host;
var recommendation_redirect_url = base_url + '/browse';
var api_url = base_url + '/api';

$( function() {

  $.support.cors = true

  requests = {
    get: function(url, callback) {
      $.get(url, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    post: function(url, data, callback) {
      $.post(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    put: function(url, data, callback) {
      $.put(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },
  };

  var formData = {};
  var winner = {}

  var candidates = [];
  var candidateIndex = 0;

  var observations = [];

  var $noSelectionMessage = $('#no-selections-message');

  var aspects;

  if (window.location.pathname === '/submit') {
    $.ajax({
      type: 'GET',
      url: '/api/aspects',
      success: function(data) {
        aspects = data.aspects;
      }
    });
  }

  function selectBestBook(title, image, olid) {
    formData['winner'] = olid;

    winner = {
      title: title,
      image: image,
      olid: olid
    };

    var bestBookListItem = `
      <li id="best-book-preview">
        <a class="preview-link" href="https://openlibrary.org${olid}" target="_blank">
          <img src="${image}"><span class="book-title">${title}</span>
        </a>
        <span id="best-book-delete" class="list-delete">
        &times;
        </span>
      </li>`;

      $('#winner-list').append(bestBookListItem);
      $('#winner').prop('hidden', true);

      // Add to selection list
      addReviewListItem(winner, true);
      $noSelectionMessage.prop('hidden', true);

      $('#best-book-delete').on('click', function() {
        $(this).parent().remove();
        $winner = $('#winner');
        $winner.val('');
        $winner.prop('hidden', false);
        delete formData['winner'];
        winner = {};

        // remove from selection list
        $('#description').parent().parent().remove();

        if(!candidates.length) {
          $noSelectionMessage.prop('hidden', false);
        }
      })
  }


  function selectCandidateWork(title, image, olid) {
    // Store candidate data
    var candidate = {
      id: ++candidateIndex,
      title: title,
      image: image,
      olid: olid,
    };
    candidates.push(candidate);

    // Create list item and append to list
    var listItem = `
      <li id="candidate-list-item${candidateIndex}">
        <a class="preview-link" href="https://openlibrary.org${candidate.olid}" target="_blank">
          <img src="${candidate.image}"><span class="book-title">${candidate.title}</span>
        </a>
        <span id="list-delete${candidateIndex}" class="list-delete">
        &times;
        </span>
      </li>`;

    $('#candidate-list').append(listItem);

    // Add to selection review list
    addReviewListItem(candidate, false);
    $noSelectionMessage.prop('hidden', true);

    // Add delete listener
    $(`#list-delete${candidateIndex}`).on('click', function() {
      
      deleteListItem($(this).parent());

      // Remove from selection review list
      $(`#candidate-review${candidate.id}`).parent().parent().remove();
      if(!candidates.length && $.isEmptyObject(winner)) {
        $noSelectionMessage.prop('hidden', false);
      }
    });

    // Add olid to list item
    $(`#candidate-list-item${candidateIndex}`).attr('data-olid', candidate.olid)

    // Clear input and remove required attribute
    $('#candidate').val('');
    $('#candidate').removeAttr('required');
  }

  var deleteListItem = function($selector) {
    // Find and remove item from candidates list
    var olid = $selector.attr('data-olid')
    var index = -1
    for(var i = 0; i < candidates.length && index === -1; ++i) {
      if(candidates[i].olid === olid) {
        index = i;
      }
    }

    candidates.splice(index, 1);

    // Remove list item from UI
    $selector.remove()

    // If candidates list is empty, add 'required' attribute to candidate text box
    if(candidates.length === 0) {
      $('#candidate').attr('required', true)
    }
  }

  /**
   * Adds a selected work to the book review list.
   * 
   * Creates and displays a new selected work review list item.  List item
   * contains a section with the book's title and cover image (if available),
   * and a review section.
   * 
   * Each review section contains a free-form textarea for a review, and a 
   * collapsible section that contains several predefined observations that
   * can improve the review.
   * 
   * Books that are desginated as the best book on a subject will appear first
   * in the list.
   * 
   * @param {Object}  book      Contains book title, cover image, and OLID.
   * @param {boolean} isWinner  True if the book is the best book on a subject.
   */
  function addReviewListItem(book, isWinner) {
    var listItemMarkUp = `
      <li> 
    `;

    if(isWinner) {
      listItemMarkUp += `
        <div class="selection-review">
          <textarea id="description" type="text" name="selection" placeholder="The winner was chosen because..." required></textarea>
        </div>
      `;
    }
    listItemMarkUp += `
      <div class="selection-info">
        <a class="preview-link" href="https://openlibrary.org${book.olid}" target="_blank">
          <img src="${book.image}"><span class="book-title">${book.title}</span>
        </a>
      </div>
      <div>
    `;

    var observationId = (isWinner) ? "best-book-observations" : `candidate-observations-${candidateIndex}`;

    listItemMarkUp += `
      ${addObservationSection(aspects, observationId)}
      </div>
    </li>
    `

    if(isWinner) {
      $('#selection-list').prepend(listItemMarkUp);
    } else {
      $('#selection-list').append(listItemMarkUp);
    }

    addCollapsibleListeners();
  }

  /**
   * Creates markup for collapsible set of predefined observation inputs.
   * 
   * All observations nested inside of a single collapsible element, and each
   * observation is itself collapsible.  An observation consists of a category
   * that expands into a question with a set of predefined answers, displayed as
   * either radio buttons or checkboxes. 
   * 
   * @param {Array<Object>} aspectList  A list of Aspect objects.
   * @param {String} id                 A string that uniquely identifies an aspect.
   * 
   * @return {String} A string containing the HTML markup of the observations section.
   */
  function addObservationSection(aspectList, id) {
    var aspectMarkup = `
      <div class="collapsible">Additional Observations (Highly recommended):</div>
      <div class="collapsible-content nested observations">
    `;

    for(var i = 0; i < aspectList.length; ++i) {
      var className = aspectList[i].multi_choice ? "multi-choice" : "single-choice";

      aspectMarkup += `
        <div class="collapsible aspect-category">${aspectList[i].label}</div>
        <div class="collapsible-content">
          <div class="aspect-description">${aspectList[i].description}</div>
          <div class="${className}">
      `;


      for(var j = aspectList[i].schema.values.length - 1; j >= 0; --j) {
        var choiceId = `${id}-${aspectList[i].label}-${j}`;
        aspectMarkup += `
          <label class="${className}-label" for="${choiceId}">
            <input type="${aspectList[i].multi_choice ? 'checkbox' : 'radio'}" name="${aspectList[i].label}-${id}" id="${choiceId}" value="${aspectList[i].schema.values[j]}">
            ${aspectList[i].schema.values[j]}
          </label>
        `
      }

      aspectMarkup += `
          </div>
        </div>
      `;
    }

    aspectMarkup += "</div>"
    return aspectMarkup;
  }

  /**
   * Handles clicks on a collapsible element.
   * 
   * Toggles the "active" class on the collapible that was clicked, highlighting
   * expanded section headings.  Resizes the maximum height of the collapsible 
   * content divs, and the parenet element if necessary.
   * 
   * @param {ClickEvent} event
   */
  function collapseHandler(event) {
    this.classList.toggle("active");
    var content = this.nextElementSibling;

    if(content.style.maxHeight) {
      content.style.maxHeight = null;
    } else {
      if(content.parentElement.classList.contains("nested")) {
        adjustMaxHeight(content.parentElement, content.scrollHeight);
      }

      content.style.maxHeight = content.scrollHeight + "px";
    }
  }

  /**
   * Adds a collapsible handler to all collapsible elements.
   */
  function addCollapsibleListeners() {
    var collapsibles = document.getElementsByClassName("collapsible");

    for(var i = 0; i < collapsibles.length; ++i) {
      collapsibles[i].addEventListener("click", collapseHandler);
    }

  }

  /**
   * Resizes the given element by its scroll height plus an additional amount.
   * 
   * This function is used to resize a parent element when one of its collapsible
   * children are expanded.  The additional height should be equal to the child's scroll
   * height.
   * 
   * @param {HTMLElement} element     The element being resized
   * @param {Number} additionalHeight Additional amount by which to resize the element.
   */
  function adjustMaxHeight(element, additionalHeight) {
    element.style.maxHeight = (element.scrollHeight + additionalHeight) + "px";
  }

  /* This is the main function which registers a <input class="ui-widget">
     as an autocomplete
  */
  var bind_autocomplete = function(self, selector, callback) {
    $(selector).autocomplete({
      source: function (request, response) {
          $.ajax(callback(request, response));
      },
      minLength: 2,
      focus: function (event, ui) {
        $(event.target).val(ui.item.label);
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);
        return false;
      },
      select: function (event, ui) {
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);

        var targetId = event.target.id;
        switch(targetId) {
          case 'topic':
            formData[targetId] = ui.item.label;
            break;
          case 'candidate':
            selectCandidateWork(ui.item.label, ui.item.img, ui.item.value);
            break;
          case 'winner':
            selectBestBook(ui.item.label, ui.item.img, ui.item.value);
            break;
        }

        return false;
      }
    }).data("ui-autocomplete")._renderItem = function (ul, item) {
      /* Renders how the data appears in the autocomplete menu */
      // NOTE: I think we only want to do this for search_books (and not search_topics)
      return $("<li />")
        .data( "ui-autocomplete-item", item)
        .append("<a class='book-result'><img src='" + item.img + "' />" + item.label + "</a>")
        .appendTo(ul);
    };
  }

  var search_books = function(request, response) {
    return {
      url: 'https://openlibrary.org/search.json?limit=10&q=' + request.term,
      success: function(resp) {
        var entities = $.map(resp.docs, function(book) {
          return {
            label: book.title,
            value: book.key,
            img: 'https://covers.openlibrary.org/b/olid/' + book.cover_edition_key + '-S.jpg'
          }
        });
        response(entities);
      }
    }
  };

  var search_topics = function(request, response) {
    return {
      url: api_url + '/topics?query=' + request.term + '&field=name&action=search',
      success: function(resp) {
        var entities = $.map(resp.topics, function(topic) {
          return {
            label: topic.name,
            value: topic.id,
	    img: ''
          }
        });

        entities.push({
          label: $('.book-topic-selector').autocomplete('instance').term,
          value: '',
          img: '',
          lastItem: true
        });
        response(entities);
      }
    }
  };

  var suggest_topic = function(topic) {
    $.ajax({
      type: 'POST',
      url: '/api/topics',
      contentType: 'application/json',
      data: JSON.stringify(topic)
    });
  }

  if ($('#recommendations-form').length) {
    $(this).on('submit', function(event) {
      event.preventDefault()

      setObservations();

      formData.candidates = [];

      for(var i = 0; i < candidates.length; ++i) {
        formData.candidates.push(candidates[i].olid);
      }

      let $description = $('#description');

      if($description.length) {
        // Sets whitespace only description to an empty string, 
        // which will trigger UI hint from browser
        $description.val($description.val().trim());
        formData.description = $description.val();
      }

      if(validateRecommendationFormData()) {
        formData.observations = [];

        // Set work OLID for each observation
        for(var i = 0; i < observations.length; ++i) {
          // Check that observations array has at least one observation:
          if(observations[i].observations.length) {
            var currentObservation = observations[i];

            // Best book will be in the first index
            if(i === 0){
              currentObservation.work_id = winner.olid;
            } else {
              currentObservation.work_id = candidates[i - 1].olid;
            }

            formData.observations.push(JSON.stringify(currentObservation));
          }
        }
        
        // TODO: Handle failure cases (server error)
        $.ajax({
          type: 'POST',
          url: '/submit',
          data: formData,
          success: function() {
            window.location = recommendation_redirect_url;
          }
        })
      } else {
        let header = 'Invalid Submission';
        let body = `Please ensure that you've selected the topic and 
        books from the autocomplete options and that the review field
        has been filled out.`;

        displayModal(header, body);
      }
    })
  }

  /**
   * Stores the names and values of all observations in each review.
   * 
   * Composes an observation object for each review section in the form.
   * Observation objects include key value pairs for each of the checked
   * inputs in a section, with the keys being the value of the Aspect's
   * label field.
   * 
   * Observation objects are stored in the `observations` array in the order
   * that they appear in the form.
   */
  function setObservations() {
    observations = [];
    var $observationSections = $('.observations');

    $observationSections.each(function(index) {
      let observationsObject = {};
      observationsObject.observations = [];

      $(this).find('input[type=radio]:checked').each(function() {
        var keyValuePair = {};
        keyValuePair[$(this).attr('name').split('-')[0]] = $(this).val();
        observationsObject.observations.push(keyValuePair);
      });

      $(this).find('input[type=checkbox]:checked').each(function() {
        var keyValuePair = {};
        keyValuePair[$(this).attr('name').split('-')[0]] = $(this).val();
        observationsObject.observations.push(keyValuePair);
      });

      observations[index] = observationsObject;
    });
  }

  /**
   * Validates recommendation form data before the form is submitted.
   * 
   * Valid form data will contain the following fields: topic, winner, description,
   * and candidates (which is an array).  There must be at least one candidate in
   * the candidates array.  Both the winner and each candidate most contain a valid 
   * olid.
   * 
   * @returns {boolean} True if form data is valid, false otherwise.
   */
  function validateRecommendationFormData() {
    if (!formData.topic || 
        !formData.winner ||
        !formData.description ||
        !formData.candidates) {
      return false;
    }

    if (!formData.candidates.length) {
      return false;
    }

    let validOlidRe = /OL[0-9]+[MW]/i;
    if (!validOlidRe.test(formData.winner)) {
      return false;
    }
    
    for (const candidate of formData.candidates) {
      if(!validOlidRe.test(candidate)) {
        return false;
      }
    }

    return true;
  }

  /**
   * Displays an information modal.
   * 
   * Creates and displays a modal with the given header and body.
   * Listens for clicks outside of the modal and on the modal close
   * symbol (X), and removes the modal on these events.
   * 
   * @listens window.onclick
   * @listens .modal.onclick
   * 
   * @param {string} header   Text that will be displayed in the modal's header.
   * @param {string} body     Text that will be displayed in the modal's body.
   */
  function displayModal(header, body) {
    let modalMarkup = `
      <div id="modal" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <span id="modal-close">&times;</span>
            <h2>${header}</h2>
          </div>
          <div class="modal-body">
            <p>${body}</p>
          </div>
        </div>
      </div>
    `
    let $modal = $(modalMarkup);

    $('body').append($modal);

    window.onclick = function(event) {
      if (event.target == document.querySelector('#modal')) {
        $modal.remove();
      }
    }

    $('#modal-close').on('click', function() {
      $modal.remove();
    })
  }

  if ($(".book-winner-selector").length) { bind_autocomplete(self, ".book-winner-selector", search_books); }
  if ($("#candidate").length) { bind_autocomplete(self, "#candidate", search_books); }
  if ($(".book-topic-selector").length) {
    bind_autocomplete(self, ".book-topic-selector", search_topics);

    var render = $('.book-topic-selector').autocomplete('instance')._renderMenu;

    $('.book-topic-selector').autocomplete('instance')._renderMenu = function(ul, items) {
      render.call(this, ul, items);

      $('#add-topic').on('click', function(event) {
        event.preventDefault();

        var topic = {
          topic: $('.book-topic-selector').autocomplete('instance').term
        }

        suggest_topic(topic);
      });
    }


    var renderItem = $('.book-topic-selector').autocomplete('instance')._renderItem;

    $(".book-topic-selector").autocomplete('instance')._renderItem = function(ul, item) {
      if(item.lastItem) {
        return $("<li />").append(
          'Topic not found. Add <a id="add-topic" href="javascript:;">' +
          $(".book-topic-selector").autocomplete('instance').term + '?</a>'
        ).appendTo(ul);
      }
      return renderItem.call(this, ul, item);
    }
  }
});

/* Admin functions: */
function approveRequest(requestId) {
  let payload = { approved: true }

  $.ajax({
    type: 'POST',
    url: `/api/requests/${requestId}`,
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(msg) {
      updateButtonGroup(requestId, msg);
    }
  })

}

function rejectRequest(requestId) {
  $.ajax({
    type: 'DELETE',
    url: `/api/requests/${requestId}`,
    success: function(msg) {
      updateButtonGroup(requestId, msg);
    }
  })
}

function approveRecommendation(recommendationId) {
  let payload = { approved: true }

  $.ajax({
    type: 'POST',
    url: `/api/recommendations/${recommendationId}`,
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(msg) {
      updateButtonGroup(recommendationId, msg);
    }
  })
}

function rejectRecommendation(button, recommendationId) {

  if (button.classList.contains('btn-danger-confirm')) {
    $.ajax({
      type: 'DELETE',
      url: `/api/recommendations/${recommendationId}`,
      success: function(msg) {
        updateButtonGroup(recommendationId, msg);
      }
    })
  } else {
    button.classList.add('btn-danger-confirm');
    button.classList.remove('btn-danger')
    setTimeout(function() {
      button.textContent = "Confirm";
    }, 450)
    
  }

}

function updateButtonGroup(id, msg) {
  let div = $(`#button-group-${id}`)
  div.children().hide()
  div.append(`<p>${msg}</p>`)
}
