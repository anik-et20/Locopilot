--- Slide 1 ---
LEARNING MANAGEMENT
SYSTEM
Submitted by:
Aniket Vaishya
240907
ID: 240907
Faculty Mentor:
Dr. Aradhana Narang
Designation: Assistant Professor
SOET, BMU
Industry Mentor:
Mr. Attendra Sharma
Designation: Business Expansion
& Strategy Head
VentureX India
PRACTICE SCHOOL-II
School of Engineering & Technology,
BML Munjal University, 67th KM Stone, NH-8, Gurugram, Haryana 122413
August 2026

--- Slide 2 ---
OUTLINE OF THE PRESENTATION
About the PS-II Station
Visit Summary
Problem Statement
Objectives of the work
Methodology
Implementation — Super Admin Portal, AI Tutor & RAG, Student Platform
Technologies Used
Results & Key achievements
Conclusions
Recommendations & Future Scope
Learning Outcomes
References
2

--- Slide 3 ---
ABOUT THE PS-II STATION
Venture X India
About the Company
Est. date: 2022
Turnover: Not disclosed
Product type: Premium Coworking & Flexible Workspace Solutions (Private Offices, Dedicated Desks, Meeting rooms, Event Spaces, Managed Office Solutions)
Number of employees: 11 – 50
Department Visited
Name of department: Technical Department
Nature of work: Full-stack web application development
Task allocated: Build LMS — a multi-role platform for students, teachers, parents, and admins
Mentors
Name: Dr. Aradhana Narang
Department: School of Engineering & Technology, BMU
Designation: Assistant Professor
Contact info: 7550160204
3

--- Slide 4 ---
WEEKLY TIMELINE
5

--- Slide 5 ---
PROBLEM STATEMENT
Educational institutions manage a vast amount of academic and administrative information through isolated, manual procedures and disconnected communication channels — leading to inefficiency, information silos and poor visibility into academic affairs.
An integrated platform is needed to streamline learning activities, track progress, manage resources and enable secure communication across all stakeholders as institutions increasingly embrace digitalization.
The Learning Management System (LearnFlow) provides a single platform for academic management, stakeholder collaboration, information sharing and efficient educational processes.
8

--- Slide 6 ---
OBJECTIVES
9
A · OVERALL PROJECT OBJECTIVES
01
Minimise academic workflow fragmentation
and give institutions a single platform for multiple education processes.
02
Build an institute-based, multi-role LMS
in which educational institutes register and administer their own academic operations.
03
Provide role-based access
for five user roles: Student, Teacher, Parent, Institution Admin and Super Admin.
04
Includes
course management, lesson management, assessment, attendance, gradebook, assignments, resources and communication  from the outset.
05
Maintain a layered, maintainable architecture
so all modules follow a consistent structure.
B · MY INDIVIDUAL OBJECTIVES
01
Develop the Super Admin module —
manage institutions, users, roles and overall LMS administration from a centralized dashboard.
02
Build the AI Tutor module—
to provide an intelligent, interactive learning assistant for students using AI-based question answering and academic support.
03
Design and implement the Functional Schema
to define the system’s functional structure, relationships and workflows across the LMS modules.
04
Integrate my modules with the LMS backend
ensuring smooth interaction between APIs, database models and the existing system architecture..
05
Test and validate the developed functionality
by verifying API operations, handling edge cases and ensuring reliable integration with the overall LMS.

--- Slide 7 ---
METHODOLOGY
ASSUMPTIONS MADE
Three assumptions framed development, based on the project scope and discussions with the industry mentor.
01
Scope — the institute-based model was adopted as final
The original company-centric approach was reviewed by the industry mentor, found architecturally over-complex, and simplified. Educational institutes register on the platform and administer their own academic operations.
02
Super Admin requires centralized administrative control
It was assumed that the Super Admin would need a dedicated interface to manage and oversee key platform entities while maintaining appropriate role-based access and data consistency.
03
AI Tutor should support conversational interaction
The initial implementation focused on PDF-based question answering. It was later assumed that a chatbot-style conversational interface would provide a more natural and continuous learning experience, allowing students to interact with the AI Tutor through multiple questions and responses.

--- Slide 8 ---
METHODOLOGY
REQUIREMENT ANALYSIS & SYSTEM UNDERSTANDING
Studied overall LMS architecture, major modules, user roles and workflows before making changes
Focused analysis on the Super Admin Portal and the Student Platform — existing interface, functionality & requirements reviewed first
Analyzed the AI Tutor / RAG requirements: query–response flow, document search, embedding generation and LLM integration
Approach for each component finalized through discussions with team members and mentors
This understanding fed directly into the functional schema, Super Admin features, RAG application and frontend changes

--- Slide 9 ---
FUNCTIONAL SCHEMA DEVELOPMENT
LMS Requirements
& User Roles
Workflows &
UI Screens
Functional
Schema (F001–F062)
Mapped to ER
Diagram (21 tables)
Mapped to
UI Components
The functional schema captured every LMS function's purpose, inputs, logic, outputs, tables and roles
Cross-referenced with the 21-table ER diagram and UI screens to ensure functionality, data and interface stayed consistent
Served as a reference guide throughout subsequent development activities

--- Slide 10 ---
SUPER ADMIN PORTAL DEVELOPMENT
Evaluated the existing portal structure and administration workflows to identify required features
Implemented administrative interfaces matching the existing LMS design and navigation patterns
Built modules including Organization Dashboard, Branches, Branch Admins, Teachers, Students, Parents and Reports
Frontend built with React and TypeScript; all features integrated with existing UI, functional requirements and data structures
After evaluation with the industry mentor, the portal was set aside from the current release scope to keep system complexity manageable

--- Slide 11 ---
SUPER ADMIN PORTAL — SCREENSHOTS
Fig — Organization Dashboard
Fig — Branch Admins
Centralized view of branches, students, teachers & revenue
Branch-level admin management with status tracking

--- Slide 12 ---
AI TUTOR — RAG ARCHITECTURE
Phase 1: Ingestion
PDF Upload /
Knowledge Source
Recursive
Chunking
Jina Embeddings
(vectors)
Store in
Vector DB
Phase 2: Querying
User
Question
Query
Embedding
Semantic
Retrieval (Top-K)
Generated
Response
Knowledge source processed and split into chunks; Jina embeddings generate semantic vectors, stored for retrieval
On a query, the most relevant chunks are retrieved and passed as context to a Groq-hosted LLM for response generation
Grounds responses in relevant context rather than relying only on the LLM's general knowledge
Pipeline tested across varied user queries to validate response relevance
23
Groq LLM + context

--- Slide 13 ---
AI TUTOR — INTERFACE & FEATURES
Fig — AI Tutor chatbot interface
Built the AI Tutor frontend (previously missing from the LMS) and integrated it end-to-end with the RAG backend
PDF-based, context-aware question answering, RAG-powered contextual responses
General AI chatbot when no document is supplied

--- Slide 14 ---
STUDENT PLATFORM FRONTEND ENHANCEMENTS
Studied the existing Student Platform's component structure, navigation flow and design principles before changing it
Updated and improved frontend components while preserving the LMS's existing visual design language
Enhancements tested and debugged to resolve interface and functionality issues
Gave practical experience modifying a live, production-oriented interface rather than building from scratch

--- Slide 15 ---
TECHNOLOGIES USED
LAYER
TECHNOLOGY
PURPOSE
Frontend
React
Teacher dashboard, quiz, and academic-module user interfaces
Backend
Node.js, Express.js
REST API layer (Routes → Controller → Service)
Database
PostgreSQL
Relational data storage for users, courses, quizzes, attendance, etc.
AI Tutor
RAG, Embeddings, LLM
Provides context-aware responses by retrieving relevant learning content and generating answers using an LLM
Authentication
JWT, role-based checks
Login, session, and role/ownership-based access control
API testing
Postman
Manual verification of endpoints, validation, and authorization
Deployment
Vercel
Hosting of backend and frontend, including production auth/proxy fixes

--- Slide 16 ---
RESULTS & KEY ACHIEVEMENTS
Functional Diagram: prepared and cross-checked against the ER diagram and UI for full consistency
LMS Architecture Analysis: examined how all users, modules and components interact
Super Admin Portal: built and validated; consciously descoped after mentor review for future large-scale deployment
RAG Application: built using Jina embeddings for semantic retrieval and Groq-based LLM for generation
AI Tutor: delivered an interactive, PDF-aware learning assistant
Student Portal: frontend improvements delivered in line with existing design
Testing & Validation: verified through multiple queries and interaction scenarios
Version Control & Teamwork: managed via Git and GitHub throughout

--- Slide 17 ---
CONCLUSIONS
The Practice School-II internship at Venture X India allowed me to contribute to something with real stakes — a multi-purpose Learning Management System designed by a student group, rather than an exercise assigned as a classroom task.
WHAT WAS DELIVERED
Super Admin Portal frontend development, workflow design and feature integration.
Frontend and UX enhancements made the platform more user-friendly and responsive
The AI Tutor / RAG pipeline demonstrated the value of context-grounded AI in an educational setting
HOW IT WAS BUILT
The project used a layered backend architecture and a relatively structured development process, with API testing and frontend integration used to confirm the functionality of the features developed.
BEYOND THE PROGRAMMING
The internship gave me practical experience of frontend development, making RAG application, API creation, authorization, testing, debugging and team programming — working within a codebase shared by multiple developers rather than in isolation.
Frontend development
RAG application
API creation
Authorization
Testing
Debugging

--- Slide 18 ---
RECOMMENDATIONS & FUTURE SCOPE
Reintroduce the Super Admin Portal for large-scale, multi-branch/organization deployment
Extend the AI Tutor with conversation history and personalized, subject-specific learning assistance
Add context-aware AI Tutor support tied to individual learning videos for in-lecture questions
Introduce timestamp-aware video assistance, pointing students to the exact lecture moment for an answer
Conduct scalability and performance testing as users, courses, documents and AI interactions grow

--- Slide 19 ---
LEARNING OUTCOMES
Hands-on experience converting business requirements into a functional schema and system processes
Strengthened frontend development skills using React and TypeScript
Learned to integrate frontend components with backend services for dynamic data handling
Gained practical exposure to embeddings, semantic retrieval, prompts and RAG-based LLM integration
Improved debugging, testing, technical documentation and presentation skills

--- Slide 20 ---
References
Pressman, R. S., & Maxim, B. R. (2020). Software engineering: A practitioner's approach (9th ed.). McGraw-Hill Education.
Sommerville, I. (2016). Software engineering (10th ed.). Pearson.
Dennis, A., Wixom, B. H., & Tegarden, D. (2020). Systems analysis and design: An object-oriented approach with UML (6th ed.).
Wiley. Wiegers, K. E., & Beatty, J. (2013). Software requirements (3rd ed.). Microsoft Press.
Larman, C. (2004). Applying UML and patterns: An introduction to object-oriented analysis and design and iterative development (3rd ed.). Pearson Education.
Ellis, R. K. (2009). A field guide to learning management systems. ASTD Learning Circuits.
Almaiah, M. A., Al-Khasawneh, A., & Althunibat, A. (2020). Exploring the critical challenges and factors influencing the e-learning system usage during the COVID-19 pandemic. Education and Information Technologies, 25(6), 5261–5280.