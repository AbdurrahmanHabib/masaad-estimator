# Gemini API reference

This API reference describes the standard, streaming, and realtime APIs you can
use to interact with the Gemini models. You can use the REST APIs in any
environment that supports HTTP requests. Refer to the
[Quickstart guide](https://ai.google.dev/gemini-api/docs/quickstart) for how to
get started with your first API call. If you're looking for the references for
our language-specific libraries and SDKs, go to the link for that language in
the left navigation under **SDK references**.

## Primary endpoints

The Gemini API is organized around the following major endpoints:

- **Standard content generation ([`generateContent`](https://ai.google.dev/api/generate-content#method:-models.generatecontent)):** A standard REST endpoint that processes your request and returns the model's full response in a single package. This is best for non-interactive tasks where you can wait for the entire result.
- **Streaming content generation ([`streamGenerateContent`](https://ai.google.dev/api/generate-content#method:-models.streamGenerateContent)):** Uses Server-Sent Events (SSE) to push chunks of the response to you as they are generated. This provides a faster, more interactive experience for applications like chatbots.
- **Live API ([`BidiGenerateContent`](https://ai.google.dev/api/live#send-messages)):** A stateful WebSocket-based API for bi-directional streaming, designed for real-time conversational use cases.
- **Batch mode ([`batchGenerateContent`](https://ai.google.dev/api/batch-mode)):** A standard REST endpoint for submitting batches of `generateContent` requests.
- **Embeddings ([`embedContent`](https://ai.google.dev/api/embeddings)):** A standard REST endpoint that generates a text embedding vector from the input `Content`.
- **Gen Media APIs:** Endpoints for generating media with our specialized models such as [Imagen for image generation](https://ai.google.dev/api/models#method:-models.predict), and [Veo for video generation](https://ai.google.dev/api/models#method:-models.predictlongrunning). Gemini also has these capabilities built in which you can access using the `generateContent` API.
- **Platform APIs:** Utility endpoints that support core capabilities such as [uploading files](https://ai.google.dev/api/files), and [counting tokens](https://ai.google.dev/api/tokens).

## Authentication

All requests to the Gemini API must include an `x-goog-api-key` header with your
API key. Create one with a few clicks in [Google AI
Studio](https://aistudio.google.com/app/apikey).

The following is an example request with the API key included in the header:  

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works in a few words"
              }
            ]
          }
        ]
      }'

For instructions on how to pass your key to the API using Gemini SDKs,
see the [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) guide.

## Content generation

This is the central endpoint for sending prompts to the model. There are two
endpoints for generating content, the key difference is how you receive the
response:

- **[`generateContent`](https://ai.google.dev/api/generate-content#method:-models.generatecontent)
  (REST)**: Receives a request and provides a single response after the model has finished its entire generation.
- **[`streamGenerateContent`](https://ai.google.dev/api/generate-content#method:-models.streamgeneratecontent)
  (SSE)**: Receives the exact same request, but the model streams back chunks of the response as they are generated. This provides a better user experience for interactive applications as it lets you display partial results immediately.

### Request body structure

The [request body](https://ai.google.dev/api/generate-content#request-body) is a JSON object that is
**identical** for both standard and streaming modes and is built from a few core
objects:

- [`Content`](https://ai.google.dev/api/caching#Content) object: Represents a single turn in a conversation.
- [`Part`](https://ai.google.dev/api/caching#Part) object: A piece of data within a `Content` turn (like text or an image).
- `inline_data` ([`Blob`](https://ai.google.dev/api/caching#Blob)): A container for raw media bytes and their MIME type.

At the highest level, the request body contains a `contents` object, which is a
list of `Content` objects, each representing turns in conversation. In most
cases, for basic text generation, you will have a single `Content` object, but
if you'd like to maintain conversation history, you can use multiple `Content`
objects.

The following shows a typical `generateContent` request body:  

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
              "role": "user",
              "parts": [
                  // A list of Part objects goes here
              ]
          },
          {
              "role": "model",
              "parts": [
                  // A list of Part objects goes here
              ]
          }
        ]
      }'

### Response body structure

The [response body](https://ai.google.dev/api/generate-content#response-body) is similar for both
the streaming and standard modes except for the following:

- Standard mode: The response body contains an instance of [`GenerateContentResponse`](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse).
- Streaming mode: The response body contains a stream of [`GenerateContentResponse`](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse) instances.

At a high level, the response body contains a `candidates` object, which is a
list of `Candidate` objects. The `Candidate` object contains a `Content`
object that has the generated response returned from the model.

## Request examples

The following examples show how these components come together for different
types of requests.

### Text-only prompt

A simple text prompt consists of a `contents` array with a single `Content`
object. That object's `parts` array, in turn, contains a single `Part` object
with a `text` field.  

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works in a single paragraph."
              }
            ]
          }
        ]
      }'

### Multimodal prompt (text and image)

To provide both text and an image in a prompt, the `parts` array should contain
two `Part` objects: one for the text, and one for the image `inline_data`.  

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d '{
        "contents": [{
        "parts":[
            {
                "inline_data": {
                "mime_type":"image/jpeg",
                "data": "/9j/4AAQSkZJRgABAQ... (base64-encoded image)"
                }
            },
            {"text": "What is in this picture?"},
          ]
        }]
      }'

### Multi-turn conversations (chat)

To build a conversation with multiple turns, you define the `contents` array
with multiple `Content` objects. The API will use this entire history as context
for the next response. The `role` for each `Content` object should alternate
between `user` and `model`.
**Note:** The client SDKs provide a chat interface that manages this list for you automatically. When using the REST API, you are responsible for maintaining the conversation history.  

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "role": "user",
            "parts": [
              { "text": "Hello." }
            ]
          },
          {
            "role": "model",
            "parts": [
              { "text": "Hello! How can I help you today?" }
            ]
          },
          {
            "role": "user",
            "parts": [
              { "text": "Please write a four-line poem about the ocean." }
            ]
          }
        ]
      }'

### Key takeaways

- `Content` is the envelope: It's the top-level container for a message turn, whether it's from the user or the model.
- `Part` enables multimodality: Use multiple `Part` objects within a single `Content` object to combine different types of data (text, image, video URI, etc.).
- Choose your data method:
  - For small, directly embedded media (like most images), use a `Part` with `inline_data`.
  - For larger files or files you want to reuse across requests, use the File API to upload the file and reference it with a `file_data` part.
- Manage conversation history: For chat applications using the REST API, build the `contents` array by appending `Content` objects for each turn, alternating between `"user"` and `"model"` roles. If you're using an SDK, refer to the SDK documentation for the recommended way to manage conversation history.

## Response examples

The following examples show how these components come together for different
types of requests.

### Text-only response

A simple text response consists of a `candidates` array with one or more
`content` objects that contain the model's response.

The following is an example of a **standard** response:  

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "At its core, Artificial Intelligence works by learning from vast amounts of data ..."
              }
            ],
            "role": "model"
          },
          "finishReason": "STOP",
          "index": 1
        }
      ],
    }

The following is series of **streaming** responses. Each response contains a
`responseId` that ties the full response together:  

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "The image displays"
              }
            ],
            "role": "model"
          },
          "index": 0
        }
      ],
      "usageMetadata": {
        "promptTokenCount": ...
      },
      "modelVersion": "gemini-2.5-flash-lite",
      "responseId": "mAitaLmkHPPlz7IPvtfUqQ4"
    }

    ...

    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": " the following materials:\n\n*   **Wood:** The accordion and the violin are primarily"
              }
            ],
            "role": "model"
          },
          "index": 0
        }
      ],
      "usageMetadata": {
        "promptTokenCount": ...
      }
      "modelVersion": "gemini-2.5-flash-lite",
      "responseId": "mAitaLmkHPPlz7IPvtfUqQ4"
    }

## Live API (BidiGenerateContent) WebSockets API

Live API offers a stateful WebSocket based API for bi-directional streaming to
enable real-time streaming use cases. You can review
[Live API guide](https://ai.google.dev/gemini-api/docs/live) and the [Live API reference](https://ai.google.dev/api/live)
for more details.

## Specialized models

In addition to the Gemini family of models, Gemini API offers endpoints for
specialized models such as [Imagen](https://ai.google.dev/gemini-api/docs/imagen),
[Lyria](https://ai.google.dev/gemini-api/docs/music-generation) and
[embedding](https://ai.google.dev/gemini-api/docs/embeddings) models. You can check out
these guides under the Models section.

## Platform APIs

The rest of the endpoints enable additional capabilities to use with the main
endpoints described so far. Check out topics
[Batch mode](https://ai.google.dev/gemini-api/docs/batch-mode) and
[File API](https://ai.google.dev/gemini-api/docs/files) in the Guides section to learn more.

## What's next

If you're just getting started, check out the following guides, which will help
you understand the Gemini API programming model:

- [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
- [Gemini model guide](https://ai.google.dev/gemini-api/docs/models/gemini)

You might also want to check out the capabilities guides, which introduce different
Gemini API features and provide code examples:

- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Context caching](https://ai.google.dev/gemini-api/docs/caching)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)

## Generative Language API

The Gemini API allows developers to build generative AI applications using Gemini models. Gemini is our most capable model, built from the ground up to be multimodal. It can generalize and seamlessly understand, operate across, and combine different types of information including language, images, audio, video, and code. You can use the Gemini API for use cases like reasoning across text and images, content generation, dialogue agents, summarization and classification systems, and more.

- [REST Resource: v1beta.batches](https://ai.google.dev/api/all-methods#v1beta.batches)
- [REST Resource: v1beta.cachedContents](https://ai.google.dev/api/all-methods#v1beta.cachedContents)
- [REST Resource: v1beta.corpora](https://ai.google.dev/api/all-methods#v1beta.corpora)
- [REST Resource: v1beta.corpora.operations](https://ai.google.dev/api/all-methods#v1beta.corpora.operations)
- [REST Resource: v1beta.corpora.permissions](https://ai.google.dev/api/all-methods#v1beta.corpora.permissions)
- [REST Resource: v1beta.dynamic](https://ai.google.dev/api/all-methods#v1beta.dynamic)
- [REST Resource: v1beta.fileSearchStores](https://ai.google.dev/api/all-methods#v1beta.fileSearchStores)
- [REST Resource: v1beta.fileSearchStores.documents](https://ai.google.dev/api/all-methods#v1beta.fileSearchStores.documents)
- [REST Resource: v1beta.fileSearchStores.operations](https://ai.google.dev/api/all-methods#v1beta.fileSearchStores.operations)
- [REST Resource: v1beta.fileSearchStores.upload.operations](https://ai.google.dev/api/all-methods#v1beta.fileSearchStores.upload.operations)
- [REST Resource: v1beta.files](https://ai.google.dev/api/all-methods#v1beta.files)
- [REST Resource: v1beta.generatedFiles](https://ai.google.dev/api/all-methods#v1beta.generatedFiles)
- [REST Resource: v1beta.generatedFiles.operations](https://ai.google.dev/api/all-methods#v1beta.generatedFiles.operations)
- [REST Resource: v1beta.media](https://ai.google.dev/api/all-methods#v1beta.media)
- [REST Resource: v1beta.models](https://ai.google.dev/api/all-methods#v1beta.models)
- [REST Resource: v1beta.models.operations](https://ai.google.dev/api/all-methods#v1beta.models.operations)
- [REST Resource: v1beta.tunedModels](https://ai.google.dev/api/all-methods#v1beta.tunedModels)
- [REST Resource: v1beta.tunedModels.operations](https://ai.google.dev/api/all-methods#v1beta.tunedModels.operations)
- [REST Resource: v1beta.tunedModels.permissions](https://ai.google.dev/api/all-methods#v1beta.tunedModels.permissions)

## Service: generativelanguage.googleapis.com

To call this service, we recommend that you use the Google-provided[client libraries](https://cloud.google.com/apis/docs/client-libraries-explained). If your application needs to use your own libraries to call this service, use the following information when you make the API requests.

### Service endpoint

A[service endpoint](https://cloud.google.com/apis/design/glossary#api_service_endpoint)is a base URL that specifies the network address of an API service. One service might have multiple service endpoints. This service has the following service endpoint and all URIs below are relative to this service endpoint:

- `https://generativelanguage.googleapis.com`

## REST Resource:[v1beta.batches](https://ai.google.dev/api/batch-api#v1beta.batches)

|                                                                                                                             Methods                                                                                                                             ||
|-------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| [cancel](https://ai.google.dev/api/batch-api#v1beta.batches.cancel)                                         | `POST /v1beta/{name=batches/*}:cancel` Starts asynchronous cancellation on a long-running operation.                                               |
| [delete](https://ai.google.dev/api/batch-api#v1beta.batches.delete)                                         | `DELETE /v1beta/{name=batches/*}` Deletes a long-running operation.                                                                                |
| [get](https://ai.google.dev/api/batch-api#v1beta.batches.get)                                               | `GET /v1beta/{name=batches/*}` Gets the latest state of a long-running operation.                                                                  |
| [list](https://ai.google.dev/api/batch-api#v1beta.batches.list)                                             | `GET /v1beta/{name=batches}` Lists operations that match the specified filter in the request.                                                      |
| [updateEmbedContentBatch](https://ai.google.dev/api/batch-api#v1beta.batches.updateEmbedContentBatch)       | `PATCH /v1beta/{embedContentBatch.name=batches/*}:updateEmbedContentBatch` Updates a batch of EmbedContent requests for batch processing.          |
| [updateGenerateContentBatch](https://ai.google.dev/api/batch-api#v1beta.batches.updateGenerateContentBatch) | `PATCH /v1beta/{generateContentBatch.name=batches/*}:updateGenerateContentBatch` Updates a batch of GenerateContent requests for batch processing. |

## REST Resource:[v1beta.cachedContents](https://ai.google.dev/api/caching#v1beta.cachedContents)

|                                                                                            Methods                                                                                             ||
|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [create](https://ai.google.dev/api/caching#v1beta.cachedContents.create) | `POST /v1beta/cachedContents` Creates CachedContent resource.                                                        |
| [delete](https://ai.google.dev/api/caching#v1beta.cachedContents.delete) | `DELETE /v1beta/{name=cachedContents/*}` Deletes CachedContent resource.                                             |
| [get](https://ai.google.dev/api/caching#v1beta.cachedContents.get)       | `GET /v1beta/{name=cachedContents/*}` Reads CachedContent resource.                                                  |
| [list](https://ai.google.dev/api/caching#v1beta.cachedContents.list)     | `GET /v1beta/cachedContents` Lists CachedContents.                                                                   |
| [patch](https://ai.google.dev/api/caching#v1beta.cachedContents.patch)   | `PATCH /v1beta/{cachedContent.name=cachedContents/*}` Updates CachedContent resource (only expiration is updatable). |

## REST Resource:[v1beta.fileSearchStores](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores)

|                                                                                                                Methods                                                                                                                ||
|-----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| [create](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.create)         | `POST /v1beta/fileSearchStores` Creates an empty`FileSearchStore`.                                                         |
| [delete](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.delete)         | `DELETE /v1beta/{name=fileSearchStores/*}` Deletes a`FileSearchStore`.                                                     |
| [get](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.get)               | `GET /v1beta/{name=fileSearchStores/*}` Gets information about a specific`FileSearchStore`.                                |
| [importFile](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.importFile) | `POST /v1beta/{fileSearchStoreName=fileSearchStores/*}:importFile` Imports a`File`from File Service to a`FileSearchStore`. |
| [list](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.list)             | `GET /v1beta/fileSearchStores` Lists all`FileSearchStores`owned by the user.                                               |

## REST Resource:[v1beta.fileSearchStores.documents](https://ai.google.dev/api/file-search/documents#v1beta.fileSearchStores)

|                                                                                               Methods                                                                                                ||
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [delete](https://ai.google.dev/api/file-search/documents#v1beta.fileSearchStores.documents.delete) | `DELETE /v1beta/{name=fileSearchStores/*/documents/*}` Deletes a`Document`.                      |
| [get](https://ai.google.dev/api/file-search/documents#v1beta.fileSearchStores.documents.get)       | `GET /v1beta/{name=fileSearchStores/*/documents/*}` Gets information about a specific`Document`. |
| [list](https://ai.google.dev/api/file-search/documents#v1beta.fileSearchStores.documents.list)     | `GET /v1beta/{parent=fileSearchStores/*}/documents` Lists all`Document`s in a`Corpus`.           |

## REST Resource:[v1beta.fileSearchStores.operations](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores)

|                                                                                                     Methods                                                                                                     ||
|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [get](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.operations.get) | `GET /v1beta/{name=fileSearchStores/*/operations/*}` Gets the latest state of a long-running operation. |

## REST Resource:[v1beta.fileSearchStores.upload.operations](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.upload)

|                                                                                                            Methods                                                                                                            ||
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| [get](https://ai.google.dev/api/file-search/file-search-stores#v1beta.fileSearchStores.upload.operations.get) | `GET /v1beta/{name=fileSearchStores/*/upload/operations/*}` Gets the latest state of a long-running operation. |

## REST Resource:[v1beta.files](https://ai.google.dev/api/files#v1beta.files)

|                                                                      Methods                                                                      ||
|---------------------------------------------------------------|------------------------------------------------------------------------------------|
| [delete](https://ai.google.dev/api/files#v1beta.files.delete) | `DELETE /v1beta/{name=files/*}` Deletes the`File`.                                 |
| [get](https://ai.google.dev/api/files#v1beta.files.get)       | `GET /v1beta/{name=files/*}` Gets the metadata for the given`File`.                |
| [list](https://ai.google.dev/api/files#v1beta.files.list)     | `GET /v1beta/files` Lists the metadata for`File`s owned by the requesting project. |

## REST Resource: v1beta.media

|                                                                                                                                                                                                   Methods                                                                                                                                                                                                    ||
|--------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [upload](https://ai.google.dev/api/files#v1beta.media.upload)                                                            | `POST /v1beta/files` `POST /upload/v1beta/files` Creates a`File`.                                                                                                                                                                                                                  |
| [uploadToFileSearchStore](https://ai.google.dev/api/file-search/file-search-stores#v1beta.media.uploadToFileSearchStore) | `POST /v1beta/{fileSearchStoreName=fileSearchStores/*}:uploadToFileSearchStore` `POST /upload/v1beta/{fileSearchStoreName=fileSearchStores/*}:uploadToFileSearchStore` Uploads data to a FileSearchStore, preprocesses and chunks before storing it in a FileSearchStore Document. |

## REST Resource:[v1beta.models](https://ai.google.dev/api/models#v1beta.models)

|                                                                                                                                                                    Methods                                                                                                                                                                    ||
|---------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [asyncBatchEmbedContent](https://ai.google.dev/api/embeddings#v1beta.models.asyncBatchEmbedContent)     | `POST /v1beta/{batch.model=models/*}:asyncBatchEmbedContent` Enqueues a batch of`EmbedContent`requests for batch processing.                                                                                                         |
| [batchEmbedContents](https://ai.google.dev/api/embeddings#v1beta.models.batchEmbedContents)             | `POST /v1beta/{model=models/*}:batchEmbedContents` Generates multiple embedding vectors from the input`Content`which consists of a batch of strings represented as`EmbedContentRequest`objects.                                      |
| [batchEmbedText](https://ai.google.dev/api/palm#v1beta.models.batchEmbedText)                           | `POST /v1beta/{model=models/*}:batchEmbedText` Generates multiple embeddings from the model given input text in a synchronous call.                                                                                                  |
| [batchGenerateContent](https://ai.google.dev/api/batch-api#v1beta.models.batchGenerateContent)          | `POST /v1beta/{batch.model=models/*}:batchGenerateContent` Enqueues a batch of`GenerateContent`requests for batch processing.                                                                                                        |
| [countMessageTokens](https://ai.google.dev/api/palm#v1beta.models.countMessageTokens)                   | `POST /v1beta/{model=models/*}:countMessageTokens` Runs a model's tokenizer on a string and returns the token count.                                                                                                                 |
| [countTextTokens](https://ai.google.dev/api/palm#v1beta.models.countTextTokens)                         | `POST /v1beta/{model=models/*}:countTextTokens` Runs a model's tokenizer on a text and returns the token count.                                                                                                                      |
| [countTokens](https://ai.google.dev/api/tokens#v1beta.models.countTokens)                               | `POST /v1beta/{model=models/*}:countTokens` Runs a model's tokenizer on input`Content`and returns the token count.                                                                                                                   |
| [embedContent](https://ai.google.dev/api/embeddings#v1beta.models.embedContent)                         | `POST /v1beta/{model=models/*}:embedContent` Generates a text embedding vector from the input`Content`using the specified[Gemini Embedding model](https://ai.google.dev/gemini-api/docs/models/gemini#text-embedding).               |
| [embedText](https://ai.google.dev/api/palm#v1beta.models.embedText)                                     | `POST /v1beta/{model=models/*}:embedText` Generates an embedding from the model given an input message.                                                                                                                              |
| [generateContent](https://ai.google.dev/api/generate-content#v1beta.models.generateContent)             | `POST /v1beta/{model=models/*}:generateContent` Generates a model response given an input`GenerateContentRequest`.                                                                                                                   |
| [generateMessage](https://ai.google.dev/api/palm#v1beta.models.generateMessage)                         | `POST /v1beta/{model=models/*}:generateMessage` Generates a response from the model given an input`MessagePrompt`.                                                                                                                   |
| [generateText](https://ai.google.dev/api/palm#v1beta.models.generateText)                               | `POST /v1beta/{model=models/*}:generateText` Generates a response from the model given an input message.                                                                                                                             |
| [get](https://ai.google.dev/api/models#v1beta.models.get)                                               | `GET /v1beta/{name=models/*}` Gets information about a specific`Model`such as its version number, token limits,[parameters](https://ai.google.dev/gemini-api/docs/models/generative-models#model-parameters)and other metadata.      |
| [list](https://ai.google.dev/api/models#v1beta.models.list)                                             | `GET /v1beta/models` Lists the[`Model`s](https://ai.google.dev/gemini-api/docs/models/gemini)available through the Gemini API.                                                                                                       |
| [predict](https://ai.google.dev/api/models#v1beta.models.predict)                                       | `POST /v1beta/{model=models/*}:predict` Performs a prediction request.                                                                                                                                                               |
| [predictLongRunning](https://ai.google.dev/api/models#v1beta.models.predictLongRunning)                 | `POST /v1beta/{model=models/*}:predictLongRunning` Same as Predict but returns an LRO.                                                                                                                                               |
| [streamGenerateContent](https://ai.google.dev/api/generate-content#v1beta.models.streamGenerateContent) | `POST /v1beta/{model=models/*}:streamGenerateContent` Generates a[streamed response](https://ai.google.dev/gemini-api/docs/text-generation?lang=python#generate-a-text-stream)from the model given an input`GenerateContentRequest`. |