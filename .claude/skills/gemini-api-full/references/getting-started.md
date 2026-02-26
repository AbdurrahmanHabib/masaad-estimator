<br />

<br />

# Gemini API

The fastest path from prompt to production with Gemini, Veo, Nano Banana, and more.  

### Python

    from google import genai

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Explain how AI works in a few words",
    )

    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Explain how AI works in a few words",
      });
      console.log(response.text);
    }

    await main();

### Go

    package main

    import (
        "context"
        "fmt"
        "log"
        "google.golang.org/genai"
    )

    func main() {
        ctx := context.Background()
        client, err := genai.NewClient(ctx, nil)
        if err != nil {
            log.Fatal(err)
        }

        result, err := client.Models.GenerateContent(
            ctx,
            "gemini-2.5-flash",
            genai.Text("Explain how AI works in a few words"),
            nil,
        )
        if err != nil {
            log.Fatal(err)
        }
        fmt.Println(result.Text())
    }

### Java

    package com.example;

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateTextFromTextInput {
      public static void main(String[] args) {
        Client client = new Client();

        GenerateContentResponse response =
            client.models.generateContent(
                "gemini-2.5-flash",
                "Explain how AI works in a few words",
                null);

        System.out.println(response.text());
      }
    }

### C#

    using System.Threading.Tasks;
    using Google.GenAI;
    using Google.GenAI.Types;

    public class GenerateContentSimpleText {
      public static async Task main() {
        var client = new Client();
        var response = await client.Models.GenerateContentAsync(
          model: "gemini-2.5-flash", contents: "Explain how AI works in a few words"
        );
        Console.WriteLine(response.Candidates[0].Content.Parts[0].Text);
      }
    }

### REST

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

[Start building](https://ai.google.dev/gemini-api/docs/quickstart)  
Follow our Quickstart guide to get an API key and make your first API call in minutes.

*** ** * ** ***

## Meet the models

[auto_awesomeGemini 3 Pro
Our most intelligent model, the best in the world for multimodal understanding, all built on state-of-the-art reasoning.](https://ai.google.dev/gemini-api/docs/models#gemini-3-pro)[video_libraryVeo 3.1
Our state-of-the-art video generation model, with native audio.](https://ai.google.dev/gemini-api/docs/video)[πNano Banana and Nano Banana Pro
State-of-the-art image generation and editing models.](https://ai.google.dev/gemini-api/docs/image-generation)[sparkGemini 2.5 Pro
Our powerful reasoning model, which excels at coding and complex reasonings tasks.](https://ai.google.dev/gemini-api/docs/models#gemini-2.5-pro)[sparkGemini 2.5 Flash
Our most balanced model, with a 1 million token context window and more.](https://ai.google.dev/gemini-api/docs/models/gemini#gemini-2.5-flash)[sparkGemini 2.5 Flash-Lite
Our fastest and most cost-efficient multimodal model with great performance for high-frequency tasks.](https://ai.google.dev/gemini-api/docs/models/gemini#gemini-2.5-flash-lite)

## Explore Capabilities

[imagesmode
Native Image Generation (Nano Banana)
Generate and edit highly contextual images natively with Gemini 2.5 Flash Image.](https://ai.google.dev/gemini-api/docs/image-generation)[article
Long Context
Input millions of tokens to Gemini models and derive understanding from unstructured images, videos, and documents.](https://ai.google.dev/gemini-api/docs/long-context)[code
Structured Outputs
Constrain Gemini to respond with JSON, a structured data format suitable for automated processing.](https://ai.google.dev/gemini-api/docs/structured-output)[functions
Function Calling
Build agentic workflows by connecting Gemini to external APIs and tools.](https://ai.google.dev/gemini-api/docs/function-calling)[videocam
Video Generation with Veo 3.1
Create high-quality video content from text or image prompts with our state-of-the-art model.](https://ai.google.dev/gemini-api/docs/video)[android_recorder
Voice Agents with Live API
Build real-time voice applications and agents with the Live API.](https://ai.google.dev/gemini-api/docs/live)[build
Tools
Connect Gemini to the world through built-in tools like Google Search, URL Context, Google Maps, Code Execution and Computer Use.](https://ai.google.dev/gemini-api/docs/tools)[stacks
Document Understanding
Process up to 1000 pages of PDF files with full multimodal understanding or other text-based file types.](https://ai.google.dev/gemini-api/docs/document-processing)[cognition_2
Thinking
Explore how thinking capabilities improve reasoning for complex tasks and agents.](https://ai.google.dev/gemini-api/docs/thinking)

## Resources

[Google AI Studio
Test prompts, manage your API keys, monitor usage, and build prototypes in platform for AI builders.
Open Google AI Studio](https://aistudio.google.com)[groupDeveloper Community
Ask questions and find solutions from other developers and Google engineers.
Join the community](https://discuss.ai.google.dev/c/gemini-api/4)[menu_bookAPI Reference
Find detailed information about the Gemini API in the official reference documentation.
Read the API reference](https://ai.google.dev/api)

<br />

This quickstart shows you how to install our[libraries](https://ai.google.dev/gemini-api/docs/libraries)and make your first Gemini API request.

## Before you begin

You need a Gemini API key. If you don't already have one, you can[get it for free in Google AI Studio](https://aistudio.google.com/app/apikey).

## Install the Google GenAI SDK

### Python

Using[Python 3.9+](https://www.python.org/downloads/), install the[`google-genai`package](https://pypi.org/project/google-genai/)using the following[pip command](https://packaging.python.org/en/latest/tutorials/installing-packages/):  

    pip install -q -U google-genai

### JavaScript

Using[Node.js v18+](https://nodejs.org/en/download/package-manager), install the[Google Gen AI SDK for TypeScript and JavaScript](https://www.npmjs.com/package/@google/genai)using the following[npm command](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm):  

    npm install @google/genai

### Go

Install[google.golang.org/genai](https://pkg.go.dev/google.golang.org/genai)in your module directory using the[go get command](https://go.dev/doc/code):  

    go get google.golang.org/genai

### Java

If you're using Maven, you can install[google-genai](https://github.com/googleapis/java-genai)by adding the following to your dependencies:  

    <dependencies>
      <dependency>
        <groupId>com.google.genai</groupId>
        <artifactId>google-genai</artifactId>
        <version>1.0.0</version>
      </dependency>
    </dependencies>

### C#

Install[googleapis/go-genai](https://googleapis.github.io/dotnet-genai/)in your module directory using the[dotnet add command](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-package-add)  

    dotnet add package Google.GenAI

### Apps Script

1. To create a new Apps Script project, go to[script.new](https://script.google.com/u/0/home/projects/create).
2. Click**Untitled project**.
3. Rename the Apps Script project**AI Studio** and click**Rename**.
4. Set your[API key](https://developers.google.com/apps-script/guides/properties#manage_script_properties_manually)
   1. At the left, click**Project Settings** ![The icon for project settings](https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/settings/default/24px.svg).
   2. Under**Script Properties** click**Add script property**.
   3. For**Property** , enter the key name:`GEMINI_API_KEY`.
   4. For**Value**, enter the value for the API key.
   5. Click**Save script properties**.
5. Replace the`Code.gs`file contents with the following code:

## Make your first request

Here is an example that uses the[`generateContent`](https://ai.google.dev/api/generate-content#method:-models.generatecontent)method to send a request to the Gemini API using the Gemini 2.5 Flash model.

If you[set your API key](https://ai.google.dev/gemini-api/docs/api-key#set-api-env-var)as the environment variable`GEMINI_API_KEY`, it will be picked up automatically by the client when using the[Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries). Otherwise you will need to[pass your API key](https://ai.google.dev/gemini-api/docs/api-key#provide-api-key-explicitly)as an argument when initializing the client.

Note that all code samples in the Gemini API docs assume that you have set the environment variable`GEMINI_API_KEY`.  

### Python

    from google import genai

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    // The client gets the API key from the environment variable `GEMINI_API_KEY`.
    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Explain how AI works in a few words",
      });
      console.log(response.text);
    }

    main();

### Go

    package main

    import (
        "context"
        "fmt"
        "log"
        "google.golang.org/genai"
    )

    func main() {
        ctx := context.Background()
        // The client gets the API key from the environment variable `GEMINI_API_KEY`.
        client, err := genai.NewClient(ctx, nil)
        if err != nil {
            log.Fatal(err)
        }

        result, err := client.Models.GenerateContent(
            ctx,
            "gemini-2.5-flash",
            genai.Text("Explain how AI works in a few words"),
            nil,
        )
        if err != nil {
            log.Fatal(err)
        }
        fmt.Println(result.Text())
    }

### Java

    package com.example;

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateTextFromTextInput {
      public static void main(String[] args) {
        // The client gets the API key from the environment variable `GEMINI_API_KEY`.
        Client client = new Client();

        GenerateContentResponse response =
            client.models.generateContent(
                "gemini-2.5-flash",
                "Explain how AI works in a few words",
                null);

        System.out.println(response.text());
      }
    }

### C#

    using System.Threading.Tasks;
    using Google.GenAI;
    using Google.GenAI.Types;

    public class GenerateContentSimpleText {
      public static async Task main() {
        // The client gets the API key from the environment variable `GEMINI_API_KEY`.
        var client = new Client();
        var response = await client.Models.GenerateContentAsync(
          model: "gemini-2.5-flash", contents: "Explain how AI works in a few words"
        );
        Console.WriteLine(response.Candidates[0].Content.Parts[0].Text);
      }
    }

### Apps Script

    // See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'Explain how AI works in a few words' },
            ],
          },
        ],
      };

      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };

      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

### REST

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

## What's next

Now that you made your first API request, you might want to explore the following guides that show Gemini in action:

- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Image generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Thinking](https://ai.google.dev/gemini-api/docs/thinking)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Long context](https://ai.google.dev/gemini-api/docs/long-context)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)

<br />

To use the Gemini API, you need an API key. This page outlines how to create and manage your keys in Google AI Studio as well as how to set up your environment to use them in your code.

## API Keys

An[API key](https://cloud.google.com/api-keys/docs/overview)is an encrypted string that you can use when calling Google Cloud APIs. You can create and manage all your Gemini API Keys from the[Google AI Studio](https://aistudio.google.com/app/apikey)**API Keys**page.

Once you have an API key, you have the following options to connect to the Gemini API:

- [Setting your API key as an environment variable](https://ai.google.dev/gemini-api/docs/api-key#set-api-env-var)
- [Providing your API key explicitly](https://ai.google.dev/gemini-api/docs/api-key#provide-api-key-explicitly)

For initial testing, you can hard code an API key, but this should only be temporary since it's not secure. You can find examples for hard coding the API key in[Providing API key explicitly](https://ai.google.dev/gemini-api/docs/api-key#provide-api-key-explicitly)section.

## Google Cloud projects

[Google Cloud projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects)are fundamental to using Google Cloud services (such as the Gemini API), managing billing, and controlling collaborators and permissions. Google AI Studio provides a lightweight interface to your Google Cloud projects.

If you don't have any projects created yet, you must either create a new project or import one from Google Cloud into Google AI Studio. The**Projects** page in Google AI Studio will display all keys that have sufficient permission to use the Gemini API. Refer to the[import projects](https://ai.google.dev/gemini-api/docs/api-key#import-projects)section for instructions.

### Default project

For new users, after accepting Terms of Service, Google AI Studio creates a default Google Cloud Project and API Key, for ease of use. You can rename this project in Google AI Studio by navigating to**Projects** view in the**Dashboard** , clicking the 3 dots settings button next to a project and choosing**Rename project**. Existing users, or users who already have Google Cloud Accounts won't have a default project created.

## Import projects

Each Gemini API key is associated with a Google Cloud project. By default, Google AI Studio does not show all of your Cloud Projects. You must import the projects you want by searching for the name or project ID in the**Import Projects**dialog. To view a complete list of projects you have access to, visit the Cloud Console.

If you don't have any projects imported yet, follow these steps to import a Google Cloud project and create a key:

1. Go to[Google AI Studio](https://aistudio.google.com).
2. Open the**Dashboard**from the left side panel.
3. Select**Projects**.
4. Select the**Import projects** button in the**Projects**page.
5. Search for and select the Google Cloud project you want to import and select the**Import**button.

Once a project is imported, go to the**API Keys** page from the**Dashboard**menu and create an API key in the project you just imported.
| **Note:** For existing users, the keys are pre-populated in the imports pane based on the last 30-days of activity in AI Studio.

## Limitations

The following are limitations of managing API keys and Google Cloud projects in Google AI Studio.

- You can create a maximum of 10 project at a time from the Google AI Studio**Projects**page.
- You can name and rename projects and keys.
- The**API keys** and**Projects**pages display a maximum of 100 keys and 50 projects.
- Only API keys that have no restrictions, or are restricted to the Generative Language API are displayed.

For additional management access to your projects, visit the Google Cloud Console.

## Setting the API key as an environment variable

If you set the environment variable`GEMINI_API_KEY`or`GOOGLE_API_KEY`, the API key will automatically be picked up by the client when using one of the[Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries). It's recommended that you set only one of those variables, but if both are set,`GOOGLE_API_KEY`takes precedence.

If you're using the REST API, or JavaScript on the browser, you will need to provide the API key explicitly.

Here is how you can set your API key locally as the environment variable`GEMINI_API_KEY`with different operating systems.  

### Linux/macOS - Bash

Bash is a common Linux and macOS terminal configuration. You can check if you have a configuration file for it by running the following command:  

    ~/.bashrc

If the response is "No such file or directory", you will need to create this file and open it by running the following commands, or use`zsh`:  

    touch ~/.bashrc
    open ~/.bashrc

Next, you need to set your API key by adding the following export command:  

    export GEMINI_API_KEY=<YOUR_API_KEY_HERE>

After saving the file, apply the changes by running:  

    source ~/.bashrc

### macOS - Zsh

Zsh is a common Linux and macOS terminal configuration. You can check if you have a configuration file for it by running the following command:  

    ~/.zshrc

If the response is "No such file or directory", you will need to create this file and open it by running the following commands, or use`bash`:  

    touch ~/.zshrc
    open ~/.zshrc

Next, you need to set your API key by adding the following export command:  

    export GEMINI_API_KEY=<YOUR_API_KEY_HERE>

After saving the file, apply the changes by running:  

    source ~/.zshrc

### Windows

1. Search for "Environment Variables" in the search bar.
2. Choose to modify**System Settings**. You may have to confirm you want to do this.
3. In the system settings dialog, click the button labeled**Environment Variables**.
4. Under either**User variables** (for the current user) or**System variables** (applies to all users who use the machine), click**New...**
5. Specify the variable name as`GEMINI_API_KEY`. Specify your Gemini API Key as the variable value.
6. Click**OK**to apply the changes.
7. Open a new terminal session (cmd or Powershell) to get the new variable.

## Providing the API key explicitly

In some cases, you may want to explicitly provide an API key. For example:

- You're doing a simple API call and prefer hard coding the API key.
- You want explicit control without having to rely on automatic discovery of environment variables by the Gemini API libraries
- You're using an environment where environment variables are not supported (e.g web) or you are making REST calls.

Below are examples for how you can provide an API key explicitly:  

### Python

    from google import genai

    client = genai.Client(api_key="<var translate="no">YOUR_API_KEY</var>")

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({ apiKey: "<var translate="no">YOUR_API_KEY</var>" });

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Explain how AI works in a few words",
      });
      console.log(response.text);
    }

    main();

### Go

    package main

    import (
        "context"
        "fmt"
        "log"
        "google.golang.org/genai"
    )

    func main() {
        ctx := context.Background()
        client, err := genai.NewClient(ctx, &genai.ClientConfig{
            APIKey:  "<var translate="no">YOUR_API_KEY</var>",
            Backend: genai.BackendGeminiAPI,
        })
        if err != nil {
            log.Fatal(err)
        }

        result, err := client.Models.GenerateContent(
            ctx,
            "gemini-2.5-flash",
            genai.Text("Explain how AI works in a few words"),
            nil,
        )
        if err != nil {
            log.Fatal(err)
        }
        fmt.Println(result.Text())
    }

### Java

    package com.example;

    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentResponse;

    public class GenerateTextFromTextInput {
      public static void main(String[] args) {
        Client client = Client.builder().apiKey("<var translate="no">YOUR_API_KEY</var>").build();

        GenerateContentResponse response =
            client.models.generateContent(
                "gemini-2.5-flash",
                "Explain how AI works in a few words",
                null);

        System.out.println(response.text());
      }
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H 'Content-Type: application/json' \
      -H "x-goog-api-key: <var translate="no">YOUR_API_KEY</var>" \
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

## Keep your API key secure

Treat your Gemini API key like a password. If compromised, others can use your project's quota, incur charges (if billing is enabled), and access your private data, such as files.

### Critical security rules

- **Never commit API keys to source control.**Do not check your API key into version control systems like Git.

- **Never expose API keys on the client-side.**Do not use your API key directly in web or mobile apps in production. Keys in client-side code (including our JavaScript/TypeScript libraries and REST calls) can be extracted.

### Best practices

- **Use server-side calls with API keys**The most secure way to use your API key is to call the Gemini API from a server-side application where the key can be kept confidential.

- **Use ephemeral tokens for client-side access (Live API only):** For direct client-side access to the Live API, you can use ephemeral tokens. They come with lower security risks and can be suitable for production use. Review[ephemeral tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)guide for more information.

- **Consider adding restrictions to your key:** You can limit a key's permissions by adding[API key restrictions](https://cloud.google.com/api-keys/docs/add-restrictions-api-keys#add-api-restrictions). This minimizes the potential damage if the key is ever leaked.

For some general best practices, you can also review this[support article](https://support.google.com/googleapi/answer/6310037).

<br />

<br />

When building with the Gemini API, we recommend using the**Google GenAI SDK** . These are the official, production-ready libraries that we develop and maintain for the most popular languages. They are in[General Availability](https://ai.google.dev/gemini-api/docs/libraries#new-libraries)and used in all our official documentation and examples.
| **Note:** If you're using one of our legacy libraries, we strongly recommend you[migrate](https://ai.google.dev/gemini-api/docs/migrate)to the Google GenAI SDK. Review the[legacy libraries](https://ai.google.dev/gemini-api/docs/libraries#previous-sdks)section for more information.

If you're new to the Gemini API, follow our[quickstart guide](https://ai.google.dev/gemini-api/docs/quickstart)to get started.

## Language support and installation

The Google GenAI SDK is available for the Python, JavaScript/TypeScript, Go and Java languages. You can install each language's library using package managers, or visit their GitHub repos for further engagement:  

### Python

- Library:[`google-genai`](https://pypi.org/project/google-genai)

- GitHub Repository:[googleapis/python-genai](https://github.com/googleapis/python-genai)

- Installation:`pip install google-genai`

### JavaScript

- Library:[`@google/genai`](https://www.npmjs.com/package/@google/genai)

- GitHub Repository:[googleapis/js-genai](https://github.com/googleapis/js-genai)

- Installation:`npm install @google/genai`

### Go

- Library:[`google.golang.org/genai`](https://pkg.go.dev/google.golang.org/genai)

- GitHub Repository:[googleapis/go-genai](https://github.com/googleapis/go-genai)

- Installation:`go get google.golang.org/genai`

### Java

- Library:`google-genai`

- GitHub Repository:[googleapis/java-genai](https://github.com/googleapis/java-genai)

- Installation: If you're using Maven, add the following to your dependencies:

    <dependencies>
      <dependency>
        <groupId>com.google.genai</groupId>
        <artifactId>google-genai</artifactId>
        <version>1.0.0</version>
      </dependency>
    </dependencies>

### C#

- Library:`Google.GenAI`

- GitHub Repository:[googleapis/go-genai](https://googleapis.github.io/dotnet-genai/)

- Installation:`dotnet add package Google.GenAI`

## General availability

We started rolling out Google GenAI SDK, a new set of libraries to access Gemini API, in late 2024 when we launched Gemini 2.0.

As of May 2025, they reached General Availability (GA) across all supported platforms and are the recommended libraries to access the Gemini API. They are stable, fully supported for production use, and are actively maintained. They provide access to the latest features, and offer the best performance working with Gemini.

If you're using one of our legacy libraries, we strongly recommend you migrate so that you can access the latest features and get the best performance working with Gemini. Review the[legacy libraries](https://ai.google.dev/gemini-api/docs/libraries#previous-sdks)section for more information.

## Legacy libraries and migration

If you are using one of our legacy libraries, we recommend that you[migrate to the new libraries](https://ai.google.dev/gemini-api/docs/migrate).

The legacy libraries don't provide access to recent features (such as[Live API](https://ai.google.dev/gemini-api/docs/live)and[Veo](https://ai.google.dev/gemini-api/docs/video)) and are on a deprecation path. They will stop receiving updates on November 30th, 2025, the feature gaps will grow and potential bugs may no longer get fixed.

Each legacy library's support status varies, detailed in the following table:

|         Language          |                                     Legacy library                                      |                         Support status                         |                                                        Recommended library                                                        |
|---------------------------|-----------------------------------------------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| **Python**                | [google-generativeai](https://github.com/google-gemini/deprecated-generative-ai-python) | All support, including bug fixes, ends on November 30th, 2025. | [google-genai](https://github.com/googleapis/python-genai)                                                                        |
| **JavaScript/TypeScript** | [@google/generativeai](https://github.com/google-gemini/generative-ai-js)               | All support, including bug fixes, ends on November 30th, 2025. | [@google/genai](https://github.com/googleapis/js-genai)                                                                           |
| **Go**                    | [google.golang.org/generative-ai](https://github.com/google/generative-ai-go)           | All support, including bug fixes, ends on November 30th, 2025. | [google.golang.org/genai](https://github.com/googleapis/go-genai)                                                                 |
| **Dart and Flutter**      | [google_generative_ai](https://pub.dev/packages/google_generative_ai/install)           | Not actively maintained                                        | Use trusted community or third party libraries, like[firebase_ai](https://pub.dev/packages/firebase_ai), or access using REST API |
| **Swift**                 | [generative-ai-swift](https://github.com/google/generative-ai-swift)                    | Not actively maintained                                        | Use[Firebase AI Logic](https://firebase.google.com/products/firebase-ai-logic)                                                    |
| **Android**               | [generative-ai-android](https://github.com/google-gemini/generative-ai-android)         | Not actively maintained                                        | Use[Firebase AI Logic](https://firebase.google.com/products/firebase-ai-logic)                                                    |

**Note for Java developers:** There was no legacy Google-provided Java SDK for the Gemini API, so no migration from a previous Google library is required. You can start directly with the new library in the[Language support and installation](https://ai.google.dev/gemini-api/docs/libraries#install)section.

## Prompt templates for code generation

Generative models (e.g., Gemini, Claude) and AI-powered IDEs (e.g., Cursor) may produce code for the Gemini API using outdated or deprecated libraries due to their training data cutoff. For the generated code to use the latest, recommended libraries, provide version and usage guidance directly in your prompts. You can use the templates below to provide the necessary context:

- [Python](https://github.com/googleapis/python-genai/blob/main/codegen_instructions.md)

- [JavaScript/TypeScript](https://github.com/googleapis/js-genai/blob/main/codegen_instructions.md)

<br />

<br />

Gemini models are accessible using the OpenAI libraries (Python and TypeScript / Javascript) along with the REST API, by updating three lines of code and using your[Gemini API key](https://aistudio.google.com/apikey). If you aren't already using the OpenAI libraries, we recommend that you call the[Gemini API directly](https://ai.google.dev/gemini-api/docs/quickstart).  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Explain to me how AI works"
            }
        ]
    )

    print(response.choices[0].message)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    const response = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
            { role: "system", content: "You are a helpful assistant." },
            {
                role: "user",
                content: "Explain to me how AI works",
            },
        ],
    });

    console.log(response.choices[0].message);

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.0-flash",
        "messages": [
            {"role": "user", "content": "Explain to me how AI works"}
        ]
        }'

What changed? Just three lines!

- **`api_key="GEMINI_API_KEY"`** : Replace "`GEMINI_API_KEY`" with your actual Gemini API key, which you can get in[Google AI Studio](https://aistudio.google.com).

- **`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`:**This tells the OpenAI library to send requests to the Gemini API endpoint instead of the default URL.

- **`model="gemini-2.5-flash"`**: Choose a compatible Gemini model

## Thinking

Gemini 3 and 2.5 models are trained to think through complex problems, leading to significantly improved reasoning. The Gemini API comes with[thinking parameters](https://ai.google.dev/gemini-api/docs/thinking#levels-budgets)which give fine grain control over how much the model will think.

Gemini 3 uses`"low"`and`"high"`thinking levels, and Gemini 2.5 models use exact thinking budgets. These map to OpenAI's reasoning efforts as follows:

| `reasoning_effort`(OpenAI) | `thinking_level`(Gemini 3) | `thinking_budget`(Gemini 2.5) |
|----------------------------|----------------------------|-------------------------------|
| `minimal`                  | `low`                      | `1,024`                       |
| `low`                      | `low`                      | `1,024`                       |
| `medium`                   | `high`                     | `8,192`                       |
| `high`                     | `high`                     | `24,576`                      |

If no`reasoning_effort`is specified, Gemini uses the model's default[level](https://ai.google.dev/gemini-api/docs/thinking#levels)or[budget](https://ai.google.dev/gemini-api/docs/thinking#set-budget).

If you want to disable thinking, you can set`reasoning_effort`to`"none"`for 2.5 models. Reasoning cannot be turned off for Gemini 2.5 Pro or 3 models.  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        reasoning_effort="low",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Explain to me how AI works"
            }
        ]
    )

    print(response.choices[0].message)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    const response = await openai.chat.completions.create({
        model: "gemini-2.5-flash",
        reasoning_effort: "low",
        messages: [
            { role: "system", content: "You are a helpful assistant." },
            {
                role: "user",
                content: "Explain to me how AI works",
            },
        ],
    });

    console.log(response.choices[0].message);

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.5-flash",
        "reasoning_effort": "low",
        "messages": [
            {"role": "user", "content": "Explain to me how AI works"}
          ]
        }'

Gemini thinking models also produce[thought summaries](https://ai.google.dev/gemini-api/docs/thinking#summaries). You can use the[`extra_body`](https://ai.google.dev/gemini-api/docs/openai#extra-body)field to include Gemini fields in your request.

Note that`reasoning_effort`and`thinking_level`/`thinking_budget`overlap functionality, so they can't be used at the same time.  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "Explain to me how AI works"}],
        extra_body={
          'extra_body': {
            "google": {
              "thinking_config": {
                "thinking_budget": "low",
                "include_thoughts": True
              }
            }
          }
        }
    )

    print(response.choices[0].message)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    const response = await openai.chat.completions.create({
        model: "gemini-2.5-flash",
        messages: [{role: "user", content: "Explain to me how AI works",}],
        extra_body: {
          "google": {
            "thinking_config": {
              "thinking_budget": "low",
              "include_thoughts": true
            }
          }
        }
    });

    console.log(response.choices[0].message);

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.5-flash",
          "messages": [{"role": "user", "content": "Explain to me how AI works"}],
          "extra_body": {
            "google": {
               "thinking_config": {
                 "include_thoughts": true
               }
            }
          }
        }'

Gemini 3 supports OpenAI compatibility for thought signatures in chat completion APIs. You can find the full example on the[thought signatures](https://ai.google.dev/gemini-api/docs/thought-signatures#openai)page.

## Streaming

The Gemini API supports[streaming responses](https://ai.google.dev/gemini-api/docs/text-generation?lang=python#generate-a-text-stream).  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
      ],
      stream=True
    )

    for chunk in response:
        print(chunk.choices[0].delta)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    async function main() {
      const completion = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": "Hello!"}
        ],
        stream: true,
      });

      for await (const chunk of completion) {
        console.log(chunk.choices[0].delta.content);
      }
    }

    main();

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.0-flash",
        "messages": [
            {"role": "user", "content": "Explain to me how AI works"}
        ],
        "stream": true
      }'

## Function calling

Function calling makes it easier for you to get structured data outputs from generative models and is[supported in the Gemini API](https://ai.google.dev/gemini-api/docs/function-calling/tutorial).  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    tools = [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get the weather in a given location",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. Chicago, IL",
              },
              "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
          },
        }
      }
    ]

    messages = [{"role": "user", "content": "What's the weather like in Chicago today?"}]
    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=messages,
      tools=tools,
      tool_choice="auto"
    )

    print(response)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    async function main() {
      const messages = [{"role": "user", "content": "What's the weather like in Chicago today?"}];
      const tools = [
          {
            "type": "function",
            "function": {
              "name": "get_weather",
              "description": "Get the weather in a given location",
              "parameters": {
                "type": "object",
                "properties": {
                  "location": {
                    "type": "string",
                    "description": "The city and state, e.g. Chicago, IL",
                  },
                  "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
              },
            }
          }
      ];

      const response = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: messages,
        tools: tools,
        tool_choice: "auto",
      });

      console.log(response);
    }

    main();

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
      "model": "gemini-2.0-flash",
      "messages": [
        {
          "role": "user",
          "content": "What'\''s the weather like in Chicago today?"
        }
      ],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
              "type": "object",
              "properties": {
                "location": {
                  "type": "string",
                  "description": "The city and state, e.g. Chicago, IL"
                },
                "unit": {
                  "type": "string",
                  "enum": ["celsius", "fahrenheit"]
                }
              },
              "required": ["location"]
            }
          }
        }
      ],
      "tool_choice": "auto"
    }'

## Image understanding

Gemini models are natively multimodal and provide best in class performance on[many common vision tasks](https://ai.google.dev/gemini-api/docs/vision).  

### Python

    import base64
    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    # Function to encode the image
    def encode_image(image_path):
      with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

    # Getting the base64 string
    base64_image = encode_image("Path/to/agi/image.jpeg")

    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "What is in this image?",
            },
            {
              "type": "image_url",
              "image_url": {
                "url":  f"data:image/jpeg;base64,{base64_image}"
              },
            },
          ],
        }
      ],
    )

    print(response.choices[0])

### JavaScript

    import OpenAI from "openai";
    import fs from 'fs/promises';

    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    async function encodeImage(imagePath) {
      try {
        const imageBuffer = await fs.readFile(imagePath);
        return imageBuffer.toString('base64');
      } catch (error) {
        console.error("Error encoding image:", error);
        return null;
      }
    }

    async function main() {
      const imagePath = "Path/to/agi/image.jpeg";
      const base64Image = await encodeImage(imagePath);

      const messages = [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "What is in this image?",
            },
            {
              "type": "image_url",
              "image_url": {
                "url": `data:image/jpeg;base64,${base64Image}`
              },
            },
          ],
        }
      ];

      try {
        const response = await openai.chat.completions.create({
          model: "gemini-2.0-flash",
          messages: messages,
        });

        console.log(response.choices[0]);
      } catch (error) {
        console.error("Error calling Gemini API:", error);
      }
    }

    main();

### REST

    bash -c '
      base64_image=$(base64 -i "Path/to/agi/image.jpeg");
      curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer GEMINI_API_KEY" \
        -d "{
          \"model\": \"gemini-2.0-flash\",
          \"messages\": [
            {
              \"role\": \"user\",
              \"content\": [
                { \"type\": \"text\", \"text\": \"What is in this image?\" },
                {
                  \"type\": \"image_url\",
                  \"image_url\": { \"url\": \"data:image/jpeg;base64,${base64_image}\" }
                }
              ]
            }
          ]
        }"
    '

## Generate an image

| **Note:** Image generation is only available in the paid tier.

Generate an image:  

### Python

    import base64
    from openai import OpenAI
    from PIL import Image
    from io import BytesIO

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    response = client.images.generate(
        model="imagen-3.0-generate-002",
        prompt="a portrait of a sheepadoodle wearing a cape",
        response_format='b64_json',
        n=1,
    )

    for image_data in response.data:
      image = Image.open(BytesIO(base64.b64decode(image_data.b64_json)))
      image.show()

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });

    async function main() {
      const image = await openai.images.generate(
        {
          model: "imagen-3.0-generate-002",
          prompt: "a portrait of a sheepadoodle wearing a cape",
          response_format: "b64_json",
          n: 1,
        }
      );

      console.log(image.data);
    }

    main();

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/images/generations" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer GEMINI_API_KEY" \
      -d '{
            "model": "imagen-3.0-generate-002",
            "prompt": "a portrait of a sheepadoodle wearing a cape",
            "response_format": "b64_json",
            "n": 1,
          }'

## Audio understanding

Analyze audio input:  

### Python

    import base64
    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    with open("/path/to/your/audio/file.wav", "rb") as audio_file:
      base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')

    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "Transcribe this audio",
            },
            {
                  "type": "input_audio",
                  "input_audio": {
                    "data": base64_audio,
                    "format": "wav"
              }
            }
          ],
        }
      ],
    )

    print(response.choices[0].message.content)

### JavaScript

    import fs from "fs";
    import OpenAI from "openai";

    const client = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });

    const audioFile = fs.readFileSync("/path/to/your/audio/file.wav");
    const base64Audio = Buffer.from(audioFile).toString("base64");

    async function main() {
      const response = await client.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "Transcribe this audio",
              },
              {
                type: "input_audio",
                input_audio: {
                  data: base64Audio,
                  format: "wav",
                },
              },
            ],
          },
        ],
      });

      console.log(response.choices[0].message.content);
    }

    main();

### REST

**Note:** If you get an`Argument list too long`error, the encoding of your audio file might be too long for curl.  

    bash -c '
      base64_audio=$(base64 -i "/path/to/your/audio/file.wav");
      curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer GEMINI_API_KEY" \
        -d "{
          \"model\": \"gemini-2.0-flash\",
          \"messages\": [
            {
              \"role\": \"user\",
              \"content\": [
                { \"type\": \"text\", \"text\": \"Transcribe this audio file.\" },
                {
                  \"type\": \"input_audio\",
                  \"input_audio\": {
                    \"data\": \"${base64_audio}\",
                    \"format\": \"wav\"
                  }
                }
              ]
            }
          ]
        }"
    '

## Structured output

Gemini models can output JSON objects in any[structure you define](https://ai.google.dev/gemini-api/docs/structured-output).  

### Python

    from pydantic import BaseModel
    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    class CalendarEvent(BaseModel):
        name: str
        date: str
        participants: list[str]

    completion = client.beta.chat.completions.parse(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Extract the event information."},
            {"role": "user", "content": "John and Susan are going to an AI conference on Friday."},
        ],
        response_format=CalendarEvent,
    )

    print(completion.choices[0].message.parsed)

### JavaScript

    import OpenAI from "openai";
    import { zodResponseFormat } from "openai/helpers/zod";
    import { z } from "zod";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai"
    });

    const CalendarEvent = z.object({
      name: z.string(),
      date: z.string(),
      participants: z.array(z.string()),
    });

    const completion = await openai.chat.completions.parse({
      model: "gemini-2.0-flash",
      messages: [
        { role: "system", content: "Extract the event information." },
        { role: "user", content: "John and Susan are going to an AI conference on Friday" },
      ],
      response_format: zodResponseFormat(CalendarEvent, "event"),
    });

    const event = completion.choices[0].message.parsed;
    console.log(event);

## Embeddings

Text embeddings measure the relatedness of text strings and can be generated using the[Gemini API](https://ai.google.dev/gemini-api/docs/embeddings).  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.embeddings.create(
        input="Your text string goes here",
        model="gemini-embedding-001"
    )

    print(response.data[0].embedding)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });

    async function main() {
      const embedding = await openai.embeddings.create({
        model: "gemini-embedding-001",
        input: "Your text string goes here",
      });

      console.log(embedding);
    }

    main();

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/openai/embeddings" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "input": "Your text string goes here",
        "model": "gemini-embedding-001"
      }'

## Batch API

You can create[batch jobs](https://ai.google.dev/gemini-api/docs/batch-mode), submit them, and check their status using the OpenAI library.

You'll need to prepare the JSONL file in OpenAI input format. For example:  

    {"custom_id": "request-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Tell me a one-sentence joke."}]}}
    {"custom_id": "request-2", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Why is the sky blue?"}]}}

OpenAI compatibility for Batch supports creating a batch, monitoring job status, and viewing batch results.

Compatibility for upload and download is currently not supported. Instead, the following example uses the`genai`client for uploading and downloading[files](https://ai.google.dev/gemini-api/docs/files), the same as when using the Gemini[Batch API](https://ai.google.dev/gemini-api/docs/batch-mode#input-file).  

### Python

    from openai import OpenAI

    # Regular genai client for uploads & downloads
    from google import genai
    client = genai.Client()

    openai_client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    # Upload the JSONL file in OpenAI input format, using regular genai SDK
    uploaded_file = client.files.upload(
        file='my-batch-requests.jsonl',
        config=types.UploadFileConfig(display_name='my-batch-requests', mime_type='jsonl')
    )

    # Create batch
    batch = openai_client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    # Wait for batch to finish (up to 24h)
    while True:
        batch = client.batches.retrieve(batch.id)
        if batch.status in ('completed', 'failed', 'cancelled', 'expired'):
            break
        print(f"Batch not finished. Current state: {batch.status}. Waiting 30 seconds...")
        time.sleep(30)
    print(f"Batch finished: {batch}")

    # Download results in OpenAI output format, using regular genai SDK
    file_content = genai_client.files.download(file=batch.output_file_id).decode('utf-8')

    # See batch_output JSONL in OpenAI output format
    for line in file_content.splitlines():
        print(line)    

The OpenAI SDK also supports[generating embeddings with the Batch API](https://ai.google.dev/gemini-api/docs/batch-api#batch-embeddings). To do so, switch out the`create`method's`endpoint`field for an embeddings endpoint, as well as the`url`and`model`keys in the JSONL file:  

    # JSONL file using embeddings model and endpoint
    # {"custom_id": "request-1", "method": "POST", "url": "/v1/embeddings", "body": {"model": "ggemini-embedding-001", "messages": [{"role": "user", "content": "Tell me a one-sentence joke."}]}}
    # {"custom_id": "request-2", "method": "POST", "url": "/v1/embeddings", "body": {"model": "gemini-embedding-001", "messages": [{"role": "user", "content": "Why is the sky blue?"}]}}

    # ...

    # Create batch step with embeddings endpoint
    batch = openai_client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/embeddings",
        completion_window="24h"
    )

See the[Batch embedding generation](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_OpenAI_Compatibility.ipynb)section of the OpenAI compatibility cookbook for a complete example.

## `extra_body`

There are several features supported by Gemini that are not available in OpenAI models but can be enabled using the`extra_body`field.

**`extra_body`features**

|-------------------|-----------------------------------------------------------------|
| `cached_content`  | Corresponds to Gemini's`GenerateContentRequest.cached_content`. |
| `thinking_config` | Corresponds to Gemini's`ThinkingConfig`.                        |

### `cached_content`

Here's an example of using`extra_body`to set`cached_content`:  

### Python

    from openai import OpenAI

    client = OpenAI(
        api_key=MY_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/"
    )

    stream = client.chat.completions.create(
        model="gemini-2.5-pro",
        n=1,
        messages=[
            {
                "role": "user",
                "content": "Summarize the video"
            }
        ],
        stream=True,
        stream_options={'include_usage': True},
        extra_body={
            'extra_body':
            {
                'google': {
                  'cached_content': "cachedContents/0000aaaa1111bbbb2222cccc3333dddd4444eeee"
              }
            }
        }
    )

    for chunk in stream:
        print(chunk)
        print(chunk.usage.to_dict())

## List models

Get a list of available Gemini models:  

### Python

    from openai import OpenAI

    client = OpenAI(
      api_key="GEMINI_API_KEY",
      base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    models = client.models.list()
    for model in models:
      print(model.id)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });

    async function main() {
      const list = await openai.models.list();

      for await (const model of list) {
        console.log(model);
      }
    }
    main();

### REST

    curl https://generativelanguage.googleapis.com/v1beta/openai/models \
    -H "Authorization: Bearer GEMINI_API_KEY"

## Retrieve a model

Retrieve a Gemini model:  

### Python

    from openai import OpenAI

    client = OpenAI(
      api_key="GEMINI_API_KEY",
      base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    model = client.models.retrieve("gemini-2.0-flash")
    print(model.id)

### JavaScript

    import OpenAI from "openai";

    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });

    async function main() {
      const model = await openai.models.retrieve("gemini-2.0-flash");
      console.log(model.id);
    }

    main();

### REST

    curl https://generativelanguage.googleapis.com/v1beta/openai/models/gemini-2.0-flash \
    -H "Authorization: Bearer GEMINI_API_KEY"

## Current limitations

Support for the OpenAI libraries is still in beta while we extend feature support.

If you have questions about supported parameters, upcoming features, or run into any issues getting started with Gemini, join our[Developer Forum](https://discuss.ai.google.dev/c/gemini-api/4).

## What's next

Try our[OpenAI Compatibility Colab](https://colab.sandbox.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Get_started_OpenAI_Compatibility.ipynb)to work through more detailed examples.