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

  /* START: Code for /submit view: */
  var formData = {};
  var winner = {}
  var candidates = [];
  var candidateIndex = 0;

  /**
   * Toggles visibility of review textarea and related help message
   * 
   * Ensures that only the textarea or the help message is visible at a time. Clears
   * textarea before displaying to readers.
   * 
   * @param {boolean} textAreaVisible True if the review text area should be displayed
   */
  function showReviewTextArea(textAreaVisible) {
    let reviewContainer = document.querySelector('#winner-review')
    let textArea = document.querySelector('#description')
    let warningMessage = document.querySelector('#no-selections-message')

    if (textAreaVisible) {
      textArea.value = '';
      reviewContainer.hidden = false;
      warningMessage.hidden = true;
    } else {
      reviewContainer.hidden = true;
      warningMessage.hidden = false;
    }
  }

  function selectBestBook(title, image, olid) {
    formData['winner'] = olid;

    winner = {
      title: title,
      image: image,
      olid: olid  // This is actually the key (`/works/${work_olid}`)
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
      $('#winner').prop('hidden', true);  // Hide text input for winner search

      addSelectedListItem(winner, true);

      if (candidates.length > 0) {
        showReviewTextArea(true);
      }

      $('#best-book-delete').on('click', function() {
        $(this).parent().remove();
        $(`#list-item-${winner.olid.split('/').pop()}`).remove();

        $winner = $('#winner'); // References text input for winner search
        $winner.val('');
        $winner.prop('hidden', false);
        delete formData['winner'];
        winner = {};

        showReviewTextArea(false);
      })
  }

  function selectCandidateWork(title, image, olid) {
    // Store candidate data
    var candidate = {
      id: ++candidateIndex,
      title: title,
      image: image,
      olid: olid, // This is actually the key (`/works/${work_olid}`)
    };
    candidates.push(candidate);

    // Create list item and append to list
    var listItem = `
      <li id="candidate-list-item${candidateIndex}">
        <a class="preview-link" href="https://openlibrary.org${candidate.olid}" target="_blank">
          <img src="${candidate.image}"><span class="book-title">${candidate.title}</span>
        </a>
        <span id="list-delete-${candidateIndex}" class="list-delete">
        &times;
        </span>
      </li>`;

    $('#candidate-list').append(listItem);

    // Add to selection review list
    addSelectedListItem(candidate, false);
    if (!$.isEmptyObject(winner)) {
      showReviewTextArea(true);
    }

    // Add delete listener
    $(`#list-delete-${candidateIndex}`).on('click', function() {
      deleteListItem($(this).parent());
      $(`#list-item-${candidate.olid.split('/').pop()}`).remove();
      if(!candidates.length || $.isEmptyObject(winner)) {
        showReviewTextArea(false);
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
   * Adds a new selected work to list of all selected works.
   * 
   * Creates and displays a new selected work review list item.  List item
   * contains a section with the book's title and cover image (if available).
   * 
   * Books that are desginated as the best book on a subject will appear first
   * in the list.
   * 
   * @param {Object}  book      Contains book title, cover image, and OLID.
   * @param {boolean} isWinner  True if the book is chosen as the best book on a subject.
   */
  function addSelectedListItem(book, isWinner) {
    let olid = book.olid.split('/').pop();
    var listItemMarkUp = `
      <li id="list-item-${olid}"> 
        <div class="selection-info">
          <a class="preview-link" href="https://openlibrary.org${book.olid}" target="_blank">
            <img src="${book.image}"><span class="book-title">${book.title}</span>
          </a>
        </div>
      </li>`

    if(isWinner) {
      $('#selection-list').prepend(listItemMarkUp);
    } else {
      $('#selection-list').append(listItemMarkUp);
    }
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

    // TODO: Check for presence of winner olid in candidates array.
    // TODO: Check for duplicate works in candidates array (Optional, but should be handled server-side if not here)

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

  /* END: Code for /submit view: */
});

/* START: Code for /admin views: */
// TODO: Should these functions really be public?

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

function approveReview(reviewId) {
  let payload = { approved: true }

  $.ajax({
    type: 'POST',
    url: `/api/reviews/${reviewId}`,
    contentType: 'application/json',
    data: JSON.stringify(payload),
    success: function(msg) {
      updateButtonGroup(reviewId, msg);
    }
  })
}

function rejectReview(reviewId) {
  $.ajax({
    type: 'DELETE',
    url: `/api/reviews/${reviewId}`,
    success: function(msg) {
      updateButtonGroup(reviewId, msg);
    }
  })
}

function updateButtonGroup(id, msg) {
  let div = $(`#button-group-${id}`)
  div.children().hide()
  div.append(`<p>${msg}</p>`)
}
/* END: Code for /admin views: */
