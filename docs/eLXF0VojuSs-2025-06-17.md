### 📹 Video Information
- **Video ID:** `eLXF0VojuSs`
- **Language:** en

### 📝 Full Transcript

[Music] my name is Emil s I'm CTO at reat and uh with my partner haml uh we're going to talk about the product we built um the challenges we faced and the and how our eval framework came to the rescue and we'll also show you some results uh a little bit about us and how the product that we built came to be uh last year we tried to see if we have uh any AI play our application is designed for real estate agents and Brokers and we had a lot of features like contact management email marketing social marketing whatever uh so we realiz we realized that we have a lot of apis uh that we've built internally and we have a lot of data so naturally we came to the unique and brilliant idea that we need to build an AI agent for our real estate agents so uh I'm going to uh rewind back a year basically last year um when we started this we started with the process of creating a produ prototype uh we built this prototype using GPT uh the original GPT 3.5 uh and react framework it was very very slow and uh it was making mistakes all the time uh but when it worked it was a majestic experience it was beautiful experience so we thought okay we got the products in a demo state but now we have to take take it to production and that's when we started um uh partnering up with haml uh to uh to basically create uh a production ready uh product I'm going to show you some very very basic examples of how this product work Bas Works basically agents ask you to do things for them like create a contact for me with this information or send an email to somebody with some instructions um find me some listings because that's real estate agents uh tend to do uh or create a website for me uh so yeah we created this uh prototype then we started the Improvement of language model phase uh the problem was when we tried to make changes uh to see if we can improve it we didn't really know uh if we're improving things or not we would make a change we would invoke it a couple of times uh we would get a feeling that yeah it worked a couple of times but we don't we didn't really know what the success rate or failure rate was is it going to work 50% of times or 80% of times and it's very difficult to launch a production app when you don't really know how well it's going to function the other problem was we improved the situation we got a feeling that it's okay it's improving this situation but the moment we changed the proms it was likely that it's going to break other use cases uh and we were essentially in the dark uh and that's when we started to partner up with haml to guide us to see if we can make this app production ready I'm going to let him uh take it from here thanks Emil so what Emil described is he was able to use prompt engineering Implement rag agents so on and so forth and iterate with Just Vibe checks really fast to go from zero to one and this is a really common approach to building an MVP it actually works really well for building an MVP however in reality this approach doesn't work for that long at all it leads to stagnation and if you don't have a way of measuring progress you can't really build so in this talk what I'm going to go over is a systematic approach you can use to improve your AI consistently I'm also going to talk about how to avoid common traps and give you some resources on how to learn more because you can't learn everything in a 15-minute talk this diagram is an illustration of the recipe of this systematic approach um of creating an evaluation framework you don't have to fixate too much on the details of this diagram because I'm going to be walking through it slowly but the first thing I want to talk about is unit test and assertions so a lot of people are familiar with unit test and assertions if you have been building software but for whatever reason people tend to skip this step um and it's it's kind of the foundation for evaluation systems you don't want to jump straight to LM as a judge or generic evals you want to try to write down as many assertions and unit tests as you can about the failure modes that you're that you're experiencing with your large language model and it it really comes from looking at data so what you have on the slide here are some simple unit tests and assertions that reat wrote based upon failure modes that we observed in the data and these are not all of them there's many of these but these are just examples of like very simple things like testing if agents are working properly so emails not being sent or things like invalid placeholders or other details being repeated when they shouldn't the the details of these specific assertions don't matter what I'm trying to drive home is this is a very simple thing that people skip but it's absolutely essential because running these assertions give you immediate feedback and are almost free to run and it's really critical to your overall evaluation system if you can have them and how do you run the assertions one very reasonable way is to use CI you can outgrow CI and it may not work as you mature but one theme I want to get across is use what you have when you begin don't jump straight into tools another thing that you want to do with these assertions and unit tests is log the results to a database but when you're starting out you want to keep it simple and stupid use your existing tools so in rat's case they were already using metabase so we log these results to metabase and then use metabase to like visualize and track the results so that we could see if we're making progress on these dumb failure modes over time again my recommendation is don't buy stuff use what you have when you when you're beginning and then get into to tools later and I'll talk more about that in a minute so we talked a little bit about unit tests and assertions the next thing I want to talk about is logging and human review so it's important to log your traces um there's a lot of tools that you can use to do this this is one area where I actually do suggest using a tool right off the bat um there's a lot of commercial tools and open source tools that are listed on this slide in re's case they ended up using lsmith but more important ly then you know it's not enough to just log your traces you have to look at them otherwise there's no point in logging them and one kind of nuance here is that looking at your data is so important that I actually recommend building your own data viewing in annotation Tools in a lot of cases and the reason is because your data and application are often very unique there's a lot of domain specific stuff in your traces so in rat's case we found that tools had too much friction for us so we built our own kind of little application and you can do this very easily in something like gradio streamlet I use shiny for python it really doesn't matter but we have a lot of domain specific stuff in this like web page things that allows us to filter data in ways that are very specific to rehat but then also lots of other metadata that's associated with each Trace that is ReChat specific that where I don't have to hunt for information to evaluate a trace and then there's other things going on here this is not only a kind of a data viewing app this is also a data labeling app where it it's like facilitates human review um which I'll talk about in a second so this is the most important part if you remember anything from this talk it is you need to look at your data and you need to fight as hard as you can to remove all friction and looking at your data even down to creating your own data viewing apps if you have to and it's absolutely critical if you have any friction in looking at data people are not going to do it and it will destroy the whole process and none of this is going to work so we talked a little bit about unit test logging into your traces and human review um and you might be wondering okay like you have these tests what about the test cases what do we do about that especially when you're starting out you might not have any users so you can use LMS to synthetically generate inputs to your system so in rat's case we basically use an llm to cplay as a real estate agent and ask questions as inputs into this uh into Lucy which is their AI assistant for all the different features and the scenarios and the tools to get really good test coverage so just want to point out that using llms to synthetically generate inputs is a good way to bootstrap these test cases so we talked a little bit about unit tests logging traces um you know having a human review and so when you have a very minimal setup like this this is like the very minimal thing like a very minimal evaluation system like Bare Bones and what you want to do when you first kind of construct that is you want to test out the evaluation system so you want to do something to make progress on your AI and the easiest way to try to make progress on your AI is to do prompt engineering so what you should do is go through this loop as many times as possible uh you know try to improve your AI with prompt engineering and see if your test coverage is good are you logging your uh are you logging your traces correctly um did you remove as much friction as possible from looking at your data and it this will help you debug that but also give you the satisfaction of like making progress on your AI as well one thing I want to point out is the upshot of having an evaluation system is you get other superpowers for almost free so all of the work in fine-tuning or most of the work is data curation so we already talked about like synthetic data generation and how that interacts with the eval framework and what you can do is you can use your eval framework to kind of filter out good cases and feed that into your human review um like we showed with that application and you can start to curate data for fine tuning and also for the failed cases you have this workflow that you can use to work through those and continuously update your fine-tuning data and what we've seen over time is that the more comprehensive your eval framework is the the cost of human review goes down because you're automating more and more um of these things and getting more confidence in your data so once you have kind of this setup now you're in a position that to know whether or not you're making progress or not you have a workflow that you can use to quickly make improvements and you can start getting rid of those dumb failure modes but also now you're set up to move into more advanced things like LM as a judge because you can't express everything as an assertion um or a unit test now LM as a judge is a deep topic just outside the scope of this talk but one thing I want to point out is it's very very important to align the llm judge to a human because you need to know whether you can trust the LM as a judge you need a way a principled way of reasoning about how reliable the LM as a judge is so what I like to do is again keep it simple and stupid I like to use a spreadsheet often don't make it complicated but what I do is have a domain expert label data uh you know label the critique and in critique data and keep iterating on that until my LM as a judge is in alignment with my human judge and I have high confidence that the LM judge is doing what it's supposed to do so I'm going to go through some common mistakes that people make when building LM as evaluation systems one is not looking at your data it's easier said than done but the people don't do the best job of doing this and one key to unlocking this is to remove all the friction as I mentioned before the second one and this is just as important is focusing on tools not processes so if if you're having a conversation about evals and the first thing you start thinking about is tools that's a smell that you're not going to be successful in your evaluations people like to jump straight to the tools tell me about the tools what tools should I use it's really important to try not to use tools to begin with and try to do some of these things manually with what you already have because if you don't do that you won't be able to evaluate the tools and you you have to know what the process is before you jump straight into the tools otherwise it's going to you're going to be blindsided another common mistake is people using generic evals off the shelf so don't want to reach for generic evals you want to write evals that are very specific to your domain things like conciseness score toxicity score you know all these different evals you can get off the shelf with tools you don't want to go directly to those that's also a that you are not doing things correctly it's not that they're not valuable at all it's just that you shouldn't rely on them because they can become a crutch and then finally the other common mistake is with LM as a judge and using that too early I often find that if I'm looking at the data closely enough I can all always find plenty of assertions and failure modes it's not always the case but it's often the case so don't go to LM as a judge too early and also make sure you align LM as as a judge with a human so I'm going to flip it back over to emo he's going to talk about the results of implementing this system all right so after we got to The Virtuous um cycle that haml just displayed we were man uh we managed to rapidly increase the success rate of the llm application uh without the eval framework a project all similar to this seemed completely impossible for us uh one one thing that I've started to hear a lot is that F shot prompting is going to replace fine tuning or some Notions like that uh in our case uh we never managed to get everything that we wanted by F shot prompting even using the newer uh and smarter agents uh I wish we could I I I've seen a lot of uh Judgment of companies and products being just chat GPT rappers I wish we could just be a chat GPT rapper and manage to extract the experience we want for our users but we never uh had that opportunity because we had some really difficult cases uh one of the things that we wanted our agent to be able to do was to mix um natural language with user interface elements like this inside the output and this essentially required us to uh mix structured output and unstructured output together uh we never managed to get this working uh without fine-tuning uh reli another thing was uh feedback so sometimes the user asks in a case like this do this for me but the agent can just do that it needs uh some sort of feedback more uh input from the user again something like this was very difficult for us to execute on especially given the previous um challenge of injecting uh user interfaces inside the conversation uh and third reason that we had to um fine tune was complex commands like this uh I'm going to show a tiny video that shows how this command was executed uh but basically in this example um the user is asking uh for a very complex command that requires using like five or six different tools uh to be done uh basically what we wanted is was for it to take that input break it down into uh many different uh function calls and execute it uh so in this case I'm asking it to find me some listings with some criteria and then create a website that's what real estate agents sometimes do for their listings that they're responsible for and also an Instagram post so they want to Market it uh they want this done only for the most most expensive listing of these three so the um the application has found three listings created a website for that created and rendered an Instagram uh post video for it uh and then has prepared an email to haml including all the information about the listings um and also including theb website that was created and the Instagram story that was created also um invited Hammer uh haml to a dinner and created a follow-up task creating something like this for a non- Savvy uh real estate agent may take a couple of hours to do but using the agent um they can do it in a minute and that's essentially was not going to be possible without us using a comprehensive eval framework nailed the timing thank you guys [Music]

### 📋 Action Plan



# AI Evaluation Framework Implementation Plan

## Summary
This video discusses how to systematically evaluate and improve AI applications, specifically focusing on moving from prototype to production. It details the creation of an evaluation framework for LLM-based applications, using a real estate agent AI assistant as a case study.

## Prerequisites
- Existing AI/LLM-based application prototype
- Basic understanding of prompt engineering
- Development environment with CI/CD capabilities
- Access to logging and database systems
- Development team with AI/ML experience

## Step-by-Step Action Plan

### Phase 1: Foundation Setup (1-2 weeks)
1. Set up basic unit tests (2-3 days)
   - Create test cases based on observed failure modes
   - Implement basic assertions
   - Tools: Existing testing framework
   
2. Implement logging infrastructure (3-4 days)
   - Select logging tool (LangSmith, Weights & Biases, or similar)
   - Set up trace logging
   - Configure database storage
   - Tools: Selected logging platform, existing database

3. Create data viewing system (4-5 days)
   - Build custom viewing interface using Gradio/Streamlit/Shiny
   - Implement domain-specific filters
   - Add metadata display capabilities
   - Tools: Gradio/Streamlit/Shiny

### Phase 2: Evaluation System Implementation (2-3 weeks)
4. Develop test cases (1 week)
   - Document common use cases
   - Create edge cases
   - Design failure scenarios
   - Tools: Documentation system

5. Set up CI/CD pipeline (3-4 days)
   - Integrate unit tests
   - Configure automated testing
   - Implement results logging
   - Tools: CI/CD platform (Jenkins, GitHub Actions, etc.)

6. Create human review process (4-5 days)
   - Design review workflow
   - Build annotation tools
   - Set up review tracking
   - Tools: Custom annotation interface

### Phase 3: Monitoring & Improvement (Ongoing)
7. Implement metrics tracking (1 week)
   - Define key performance indicators
   - Set up dashboards
   - Configure alerts
   - Tools: Metabase or similar analytics platform

## Expected Outcomes
- Quantifiable measure of AI system performance
- Systematic way to track improvements
- Reduced error rates
- Better understanding of failure modes
- Data-driven decision making for improvements

## Common Pitfalls to Avoid
1. Skipping basic unit tests in favor of complex evaluations
2. Not looking at the data regularly
3. Using overly complicated tools when starting out
4. Having too much friction in the data viewing process
5. Not logging sufficient metadata
6. Failing to maintain consistent human review processes
7. Over-relying on automated metrics without human validation

## Best Practices
1. Start simple and use existing tools
2. Prioritize ease of data viewing
3. Build custom tools for domain-specific needs
4. Maintain consistent review processes
5. Document all failure modes
6. Regular team reviews of system performance
7. Iterate based on quantifiable metrics

Remember: The key to success is maintaining a systematic approach while keeping the implementation as simple as possible in the beginning stages.



---

### Summary of Key Points from the Video

This presentation discusses the development of an AI evaluation framework, specifically in the context of a real estate agent AI assistant. Here are the main takeaways:

1. **Initial Challenge**
- The team built an AI prototype using GPT-3.5 for real estate agents
- Early version was slow and error-prone
- Lacked systematic way to measure improvements

2. **Key Components of Solution**
- Implemented basic unit tests and assertions
- Set up comprehensive logging system
- Created custom data viewing tools
- Established human review process

3. **Best Practices Highlighted**
- Start simple and use existing tools
- Focus on removing friction in data viewing
- Build domain-specific evaluation tools
- Maintain consistent review processes

4. **Results**
- Successfully improved AI system reliability
- Enabled complex multi-step tasks
- Achieved production-ready performance
- Combined structured and unstructured outputs effectively

The presentation emphasizes the importance of having a systematic evaluation framework when developing AI applications, rather than relying on ad-hoc testing and "vibe checks." The speakers (Emil and Haml) provide a practical approach to building such a framework, starting with simple tools and gradually adding complexity as needed.

---

## Analysis Details

**Tools Used:** youtube_transcript
