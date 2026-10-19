/**
 * TechSift AI - Static Bilingual UI Translation Dictionaries.
 * Fully static, zero-cost, covering 100% of UI elements in English and Modern Standard Arabic.
 */

export type Language = 'en' | 'ar';

export interface Translations {
  // Brand & Header
  appTitle: string;
  appSubtitle: string;
  navDashboard: string;
  navLibrary: string;
  navSettings: string;
  apiConnected: string;
  apiDisconnected: string;
  apiChecking: string;
  zeroCostTag: string;

  // Knowledge Journey
  journeyTitle: string;
  stageUnderstand: string;
  stageUnderstandDesc: string;
  stageListen: string;
  stageListenDesc: string;
  stagePractice: string;
  stagePracticeDesc: string;
  stageMaster: string;
  stageMasterDesc: string;
  comingSoon: string;
  currentStage: string;

  // Dashboard
  dashboardTitle: string;
  dashboardSubtitle: string;
  statTotalDocs: string;
  statTotalSummaries: string;
  statProcessedDocs: string;
  statFailedDocs: string;
  quickUploadTitle: string;
  quickUploadDesc: string;
  quickUploadAction: string;
  recentDocsTitle: string;
  recentDocsViewAll: string;
  noDocsYet: string;
  noDocsYetDesc: string;
  recentActivityTitle: string;
  activityDocUploaded: string;
  activityDocProcessed: string;

  // Document Library
  libraryTitle: string;
  librarySubtitle: string;
  uploadButton: string;
  searchPlaceholder: string;
  filterAll: string;
  filterProcessed: string;
  filterPending: string;
  filterFailed: string;
  filterUnsupported: string;
  thFilename: string;
  thType: string;
  thSize: string;
  thWords: string;
  thPages: string;
  thStatus: string;
  thDate: string;
  thActions: string;
  actionOpenWorkspace: string;
  actionDelete: string;
  paginationPage: string;
  paginationOf: string;
  paginationPrev: string;
  paginationNext: string;
  dropzoneTitle: string;
  dropzoneSubtitle: string;
  dropzoneActive: string;
  supportedFormatsNotice: string;
  uploading: string;
  uploadSuccess: string;
  uploadError: string;

  // Delete Modal
  deleteModalTitle: string;
  deleteModalWarning: string;
  deleteModalPrompt: string;
  deleteModalCancel: string;
  deleteModalConfirm: string;
  deleting: string;

  // Workspace
  workspaceTitle: string;
  workspaceDocInfo: string;
  tabSummary: string;
  tabSourceText: string;
  tabHistory: string;
  controlsTitle: string;
  outputLanguageLabel: string;
  langArabic: string;
  langEnglish: string;
  detailLevelLabel: string;
  detailShort: string;
  detailShortDesc: string;
  detailStandard: string;
  detailStandardDesc: string;
  detailDetailed: string;
  detailDetailedDesc: string;
  generateSummaryBtn: string;
  generatingSummary: string;
  statusCached: string;
  statusFresh: string;
  statusPending: string;
  statusProcessing: string;
  statusCompleted: string;
  statusFailed: string;

  // Summary Viewer Sections
  sectionExecutive: string;
  sectionConcepts: string;
  sectionFindings: string;
  sectionArchitecture: string;
  sectionApplications: string;
  sectionLimitations: string;
  sectionTakeaways: string;
  sectionSources: string;
  sourcePagesLabel: string;
  sourceChunksLabel: string;
  sourceDisclaimer: string;
  noSourcePagesAvailable: string;
  relatedConceptsLabel: string;
  noSummaryYet: string;
  noSummaryYetDesc: string;
  viewingSummaryFrom: string;
  modelBadgePrefix: string;

  // Audio Studio
  tabAudio: string;
  audioModeLabel: string;
  audioModeNarration: string;
  audioModeNarrationDesc: string;
  audioModePodcast: string;
  audioModePodcastDesc: string;
  audioVoiceLabel: string;
  voiceMale: string;
  voiceFemale: string;
  voiceHost: string;
  voiceCohost: string;
  generateAudioBtn: string;
  generatingAudio: string;
  audioPlayerTitle: string;
  audioSpeed: string;
  audioDownloadMp3: string;
  audioTranscriptTitle: string;
  audioHistoryTitle: string;
  noAudioYet: string;
  noAudioYetDesc: string;
  conversationalPauseNotice: string;
  audioGeneratingCardTitle: string;
  audioGeneratingCardDesc: string;
  audioFailedCardTitle: string;
  audioFailedCardDesc: string;

  // Learning Studio
  tabLearning: string;
  learningStudioTitle: string;
  learningStudioDesc: string;
  learningDifficultyLabel: string;
  learningLanguageLabel: string;
  difficultyBeginner: string;
  difficultyBeginnerDesc: string;
  difficultyIntermediate: string;
  difficultyIntermediateDesc: string;
  difficultyAdvanced: string;
  difficultyAdvancedDesc: string;
  generateLearningPathBtn: string;
  generatingLearningPath: string;
  learningPathHistoryTitle: string;
  noLearningPathsYet: string;
  noLearningPathsYetDesc: string;
  modulesLabel: string;
  lessonsLabel: string;
  estimatedMinutesLabel: string;
  prerequisitesLabel: string;
  learningObjectivesLabel: string;
  keyConceptsLabel: string;
  exampleSnippetLabel: string;
  sourceReferencesLabel: string;
  learningGeneratingCardTitle: string;
  learningGeneratingCardDesc: string;
  learningFailedCardTitle: string;
  learningFailedCardDesc: string;
  viewPathDetails: string;
  retryGeneration: string;
  sourceReferencePill: string;

  // Phase 5B: Interactive Quizzes & Assessments
  takeLessonQuizBtn: string;
  takeModuleAssessmentBtn: string;
  takeFinalAssessmentBtn: string;
  assessmentModalTitle: string;
  questionStepLabel: string;
  submitAnswerBtn: string;
  submittingAnswer: string;
  submitAssessmentBtn: string;
  submittingAssessment: string;
  assessmentResultsTitle: string;
  assessmentScoreLabel: string;
  assessmentPassedBadge: string;
  assessmentFailedBadge: string;
  retakeAssessmentBtn: string;
  yourAnswerLabel: string;
  correctAnswerLabel: string;
  pedagogicalExplanationLabel: string;
  groundedSourceCitationLabel: string;
  assessmentGeneratingTitle: string;
  assessmentGeneratingDesc: string;
  nextQuestionBtn: string;
  prevQuestionBtn: string;

  // Phase 5C: Learning Progress & Dashboard
  tabCurriculum: string;
  tabProgressDashboard: string;
  progressOverviewTitle: string;
  completionRateLabel: string;
  completedLessonsLabel: string;
  remainingLessonsLabel: string;
  assessmentPassRateLabel: string;
  averageQuizScoreLabel: string;
  resumeLearningBtn: string;
  markLessonCompletedBtn: string;
  lessonCompletedBadge: string;
  lessonInProgressBadge: string;
  moduleProgressLabel: string;
  knowledgeMasteryTitle: string;
  strongConceptsTitle: string;
  conceptsNeedingReviewTitle: string;
  frequentlyMissedQuestionsTitle: string;
  noMissedQuestionsYet: string;
  noStrongConceptsYet: string;
  noConceptsNeedingReviewYet: string;
  smartRecommendationsTitle: string;
  noRecommendationsYet: string;
  recentAssessmentsHistoryTitle: string;
  noAssessmentsAttemptedYet: string;
  evidenceLabel: string;
  failureRateLabel: string;

  // Settings
  settingsTitle: string;
  settingsSubtitle: string;
  sectionPreferences: string;
  uiLanguageLabel: string;
  themeLabel: string;
  themeLight: string;
  themeDark: string;
  themeSystem: string;
  defaultSummaryLangLabel: string;
  defaultDetailLevelLabel: string;
  sectionSystemHealth: string;
  backendStatusLabel: string;
  backendVersionLabel: string;
  backendEnvLabel: string;
  testConnectionBtn: string;
  testingConnection: string;
  zeroCostGuaranteeTitle: string;
  zeroCostGuaranteeDesc: string;
  savePreferencesSuccess: string;

  // Common & Errors
  loading: string;
  retry: string;
  close: string;
  errorTitle: string;
  networkErrorDesc: string;
  fileTooLargeError: string;
  invalidFileFormatError: string;
  scannedPdfNotice: string;
}

export const translations: Record<Language, Translations> = {
  en: {
    // Brand & Header
    appTitle: 'TechSift AI',
    appSubtitle: 'Technical Document Intelligence Platform',
    navDashboard: 'Dashboard',
    navLibrary: 'Documents',
    navSettings: 'Settings',
    apiConnected: 'Backend Online',
    apiDisconnected: 'Backend Offline',
    apiChecking: 'Connecting...',
    zeroCostTag: 'Zero-Cost Free Tier',

    // Knowledge Journey
    journeyTitle: 'Technical Learning Workflow',
    stageUnderstand: 'Understand',
    stageUnderstandDesc: 'Deep AI-assisted architectural summarization and technical concept analysis',
    stageListen: 'Listen',
    stageListenDesc: 'Offline speech synthesis and structured audio overviews',
    stagePractice: 'Practice',
    stagePracticeDesc: 'Interactive technical flashcards and grounded self-assessment',
    stageMaster: 'Master',
    stageMasterDesc: 'RAG-grounded conversational interrogation and code extraction',
    comingSoon: 'Coming Soon',
    currentStage: 'Active Stage',

    // Dashboard
    dashboardTitle: 'System Overview',
    dashboardSubtitle: 'Real-time document ingestion metrics and learning activity',
    statTotalDocs: 'Total Documents',
    statTotalSummaries: 'Generated Summaries',
    statProcessedDocs: 'Ready for Analysis',
    statFailedDocs: 'Requires Attention',
    quickUploadTitle: 'Quick Ingest',
    quickUploadDesc: 'Drop a technical PDF, Markdown, or specification to start',
    quickUploadAction: 'Upload Document',
    recentDocsTitle: 'Recently Uploaded Documents',
    recentDocsViewAll: 'View All in Library',
    noDocsYet: 'No documents ingested yet',
    noDocsYetDesc: 'Upload a technical whitepaper, RFC, or documentation to begin analyzing.',
    recentActivityTitle: 'Recent Pipeline Activity',
    activityDocUploaded: 'Document received and validated',
    activityDocProcessed: 'Text extracted and ready for summarization',

    // Document Library
    libraryTitle: 'Document Library',
    librarySubtitle: 'Manage ingested specifications, technical whitepapers, and guides',
    uploadButton: 'Upload Document',
    searchPlaceholder: 'Search documents by filename...',
    filterAll: 'All Statuses',
    filterProcessed: 'Processed',
    filterPending: 'Pending',
    filterFailed: 'Failed',
    filterUnsupported: 'Unsupported (Scanned)',
    thFilename: 'Document Name',
    thType: 'Format',
    thSize: 'Size',
    thWords: 'Words',
    thPages: 'Pages',
    thStatus: 'Status',
    thDate: 'Ingested',
    thActions: 'Actions',
    actionOpenWorkspace: 'Open Workspace',
    actionDelete: 'Delete',
    paginationPage: 'Page',
    paginationOf: 'of',
    paginationPrev: 'Previous',
    paginationNext: 'Next',
    dropzoneTitle: 'Drag & Drop your technical document here',
    dropzoneSubtitle: 'or click to browse from your filesystem',
    dropzoneActive: 'Drop file now to begin validation...',
    supportedFormatsNotice: 'Supports PDF, TXT, and Markdown (Max 15MB). Local storage only.',
    uploading: 'Uploading & Extracting Text...',
    uploadSuccess: 'Document successfully ingested and parsed!',
    uploadError: 'Failed to upload document. Please check the file and try again.',

    // Delete Modal
    deleteModalTitle: 'Confirm Document Deletion',
    deleteModalWarning: 'This action is permanent and will remove the document, its extracted text, all generated summaries, and disk files.',
    deleteModalPrompt: 'Are you sure you want to delete:',
    deleteModalCancel: 'Cancel',
    deleteModalConfirm: 'Permanently Delete',
    deleting: 'Deleting...',

    // Workspace
    workspaceTitle: 'Document Analysis Workspace',
    workspaceDocInfo: 'Document Metadata',
    tabSummary: 'AI Technical Summary',
    tabSourceText: 'Extracted Plain Text',
    tabHistory: 'Previous Summaries',
    controlsTitle: 'Summarization Configuration',
    outputLanguageLabel: 'Summary Target Language',
    langArabic: 'Modern Standard Arabic (العربية)',
    langEnglish: 'English (Technical)',
    detailLevelLabel: 'Detail Level',
    detailShort: 'Short',
    detailShortDesc: '3-5 key concepts, rapid executive takeaways',
    detailStandard: 'Standard',
    detailStandardDesc: 'Balanced architectural summary, definitions & findings',
    detailDetailed: 'Detailed',
    detailDetailedDesc: 'Deep-dive component relationships & limitations',
    generateSummaryBtn: 'Generate AI Summary',
    generatingSummary: 'Generating Summary with Gemini...',
    statusCached: 'Retrieved from SQLite Cache (0 AI Calls)',
    statusFresh: 'Newly Generated via Gemini Free Tier',
    statusPending: 'Queued',
    statusProcessing: 'Analyzing & Synthesizing...',
    statusCompleted: 'Completed',
    statusFailed: 'Generation Failed',

    // Summary Viewer Sections
    sectionExecutive: 'Executive Summary',
    sectionConcepts: 'Core Technical Concepts & Taxonomy',
    sectionFindings: 'Key Findings & Engineering Insights',
    sectionArchitecture: 'Technical Architecture & System Design',
    sectionApplications: 'Practical Applications & Use Cases',
    sectionLimitations: 'Known Limitations & Architectural Trade-offs',
    sectionTakeaways: 'Actionable Technical Takeaways',
    sectionSources: 'Grounded Source Citations',
    sourcePagesLabel: 'Referenced Page Numbers',
    sourceChunksLabel: 'Referenced Chunk Indices',
    sourceDisclaimer: 'Citation Disclaimer',
    noSourcePagesAvailable: 'Page numbers not applicable (Plain text / Markdown document)',
    relatedConceptsLabel: 'Related Architecture Elements',
    noSummaryYet: 'No summary generated yet',
    noSummaryYetDesc: 'Select your preferred language and detail level above, then click "Generate AI Summary".',
    viewingSummaryFrom: 'Viewing summary generated at',
    modelBadgePrefix: 'Model',

    // Audio Studio
    tabAudio: 'Audio Studio',
    audioModeLabel: 'Audio Format',
    audioModeNarration: 'Technical Narration',
    audioModeNarrationDesc: 'Structured single-speaker walkthrough of key technical summaries.',
    audioModePodcast: 'Educational Podcast',
    audioModePodcastDesc: 'Dual-speaker technical discussion between Host and Co-host with 450ms natural pauses.',
    audioVoiceLabel: 'Voice & Speaker',
    voiceMale: 'Male Voice',
    voiceFemale: 'Female Voice',
    voiceHost: 'Host',
    voiceCohost: 'Co-host',
    generateAudioBtn: 'Generate Audio ($0)',
    generatingAudio: 'Synthesizing Audio...',
    audioPlayerTitle: 'Audio Player',
    audioSpeed: 'Speed',
    audioDownloadMp3: 'Download MP3',
    audioTranscriptTitle: 'Dialogue Script & Transcript',
    audioHistoryTitle: 'Generated Audio Episodes',
    noAudioYet: 'No Audio Episodes Yet',
    noAudioYetDesc: 'Generate a technical narration or podcast episode from this document.',
    conversationalPauseNotice: 'Enhanced with 450ms conversational pauses between dialogue turns',
    audioGeneratingCardTitle: 'Synthesizing Audio Episode...',
    audioGeneratingCardDesc: 'Speech synthesis and conversational audio stitching in progress.',
    audioFailedCardTitle: 'Audio Generation Failed',
    audioFailedCardDesc: 'An error occurred during audio generation. You can retry with zero cost.',

    // Learning Studio
    tabLearning: 'Learning Studio',
    learningStudioTitle: 'Interactive Technical Learning Path',
    learningStudioDesc: 'Transform technical documents into structured, source-grounded curricula with step-by-step lessons and verified citations.',
    learningDifficultyLabel: 'Target Audience & Difficulty',
    learningLanguageLabel: 'Curriculum Language',
    difficultyBeginner: 'Beginner',
    difficultyBeginnerDesc: 'Fundamental concepts, friendly explanations, and core terminology.',
    difficultyIntermediate: 'Intermediate',
    difficultyIntermediateDesc: 'Architecture deep-dive, implementation patterns, and practical trade-offs.',
    difficultyAdvanced: 'Advanced',
    difficultyAdvancedDesc: 'Production internals, edge cases, performance, and failure modes.',
    generateLearningPathBtn: 'Generate Learning Path ($0)',
    generatingLearningPath: 'Synthesizing Learning Curriculum...',
    learningPathHistoryTitle: 'Generated Curricula',
    noLearningPathsYet: 'No Learning Paths Yet',
    noLearningPathsYetDesc: 'Select target difficulty and language above to generate a grounded learning curriculum from this document.',
    modulesLabel: 'Modules',
    lessonsLabel: 'Lessons',
    estimatedMinutesLabel: 'mins',
    prerequisitesLabel: 'Prerequisites',
    learningObjectivesLabel: 'Learning Objectives',
    keyConceptsLabel: 'Key Technical Concepts',
    exampleSnippetLabel: 'Practical Example / Implementation Code',
    sourceReferencesLabel: 'Source Grounding & Citations',
    learningGeneratingCardTitle: 'Synthesizing Grounded Learning Path...',
    learningGeneratingCardDesc: 'AI is analyzing document chunks and constructing an educational path. This takes ~15-30 seconds.',
    learningFailedCardTitle: 'Learning Path Generation Failed',
    learningFailedCardDesc: 'An error occurred during curriculum synthesis. You can retry with zero cost.',
    viewPathDetails: 'Curriculum Structure',
    retryGeneration: 'Retry Generation',
    sourceReferencePill: 'Source Reference',

    // Phase 5B: Interactive Quizzes & Assessments
    takeLessonQuizBtn: 'Quiz: Test Understanding',
    takeModuleAssessmentBtn: 'Module Assessment',
    takeFinalAssessmentBtn: 'Final Comprehensive Exam',
    assessmentModalTitle: 'Interactive Assessment',
    questionStepLabel: 'Question',
    submitAnswerBtn: 'Submit Answer',
    submittingAnswer: 'Recording...',
    submitAssessmentBtn: 'Finish & Grade Assessment',
    submittingAssessment: 'Grading Attempt Locally...',
    assessmentResultsTitle: 'Assessment Results & Evaluation',
    assessmentScoreLabel: 'Final Score',
    assessmentPassedBadge: 'Passed',
    assessmentFailedBadge: 'Needs Review',
    retakeAssessmentBtn: 'Retake Assessment',
    yourAnswerLabel: 'Your Answer',
    correctAnswerLabel: 'Correct Answer',
    pedagogicalExplanationLabel: 'Explanation & Concept',
    groundedSourceCitationLabel: 'Document Grounding',
    assessmentGeneratingTitle: 'Generating Assessment Questions...',
    assessmentGeneratingDesc: 'Synthesizing source-grounded multiple choice questions from document chunks...',
    nextQuestionBtn: 'Next Question',
    prevQuestionBtn: 'Previous Question',

    // Phase 5C: Learning Progress & Dashboard
    tabCurriculum: 'Curriculum View',
    tabProgressDashboard: 'Learning Dashboard',
    progressOverviewTitle: 'Curriculum Progress Overview',
    completionRateLabel: 'Completion Rate',
    completedLessonsLabel: 'Completed Lessons',
    remainingLessonsLabel: 'Remaining Lessons',
    assessmentPassRateLabel: 'Quiz Pass Rate',
    averageQuizScoreLabel: 'Average Score',
    resumeLearningBtn: 'Resume Learning',
    markLessonCompletedBtn: 'Mark as Completed',
    lessonCompletedBadge: 'Completed',
    lessonInProgressBadge: 'In Progress',
    moduleProgressLabel: 'Module Progress',
    knowledgeMasteryTitle: 'Knowledge Mastery & Performance',
    strongConceptsTitle: 'Strong Concepts',
    conceptsNeedingReviewTitle: 'Concepts Needing Review',
    frequentlyMissedQuestionsTitle: 'Frequently Missed Questions',
    noMissedQuestionsYet: 'No frequently missed questions detected. Great job!',
    noStrongConceptsYet: 'Complete lesson quizzes with >= 70% to establish strong concepts.',
    noConceptsNeedingReviewYet: 'No concepts currently flagged for review.',
    smartRecommendationsTitle: 'Pedagogical Recommendations',
    noRecommendationsYet: 'Start reading lessons to receive personalized recommendations.',
    recentAssessmentsHistoryTitle: 'Assessment Attempt History',
    noAssessmentsAttemptedYet: 'No assessments attempted yet.',
    evidenceLabel: 'Evidence',
    failureRateLabel: 'Failure Rate',

    // Settings
    settingsTitle: 'Application Settings',
    settingsSubtitle: 'Configure interface language, appearance, and local runtime defaults',
    sectionPreferences: 'User Preferences',
    uiLanguageLabel: 'Interface Language',
    themeLabel: 'Color Theme',
    themeLight: 'Light Mode',
    themeDark: 'Dark Mode',
    themeSystem: 'System Default',
    defaultSummaryLangLabel: 'Default Summary Language',
    defaultDetailLevelLabel: 'Default Detail Level',
    sectionSystemHealth: 'Backend Connectivity & Diagnostics',
    backendStatusLabel: 'API Service Status',
    backendVersionLabel: 'API Version',
    backendEnvLabel: 'Runtime Environment',
    testConnectionBtn: 'Ping Backend Health',
    testingConnection: 'Checking...',
    zeroCostGuaranteeTitle: 'Zero-Cost Architecture Verification',
    zeroCostGuaranteeDesc: 'TechSift AI runs completely locally using SQLite (aiosqlite) and verified free-tier Google Gemini 3.8 Flash quotas. No cloud billing, no credit card required.',
    savePreferencesSuccess: 'Settings saved locally!',

    // Common & Errors
    loading: 'Loading data...',
    retry: 'Retry',
    close: 'Close',
    errorTitle: 'Operation Error',
    networkErrorDesc: 'Cannot communicate with the FastAPI backend. Make sure the server is running on http://127.0.0.1:8000.',
    fileTooLargeError: 'File exceeds maximum size limit of 15 MB.',
    invalidFileFormatError: 'Invalid file format. Please upload a PDF, TXT, or Markdown document.',
    scannedPdfNotice: 'Notice: Scanned or image-only PDFs without extractable text cannot be processed.',
  },

  ar: {
    // Brand & Header
    appTitle: 'تيك سيفت AI',
    appSubtitle: 'منصة التحليل والاستيعاب الذكي للمستندات التقنية',
    navDashboard: 'لوحة التحكم',
    navLibrary: 'المستندات',
    navSettings: 'الإعدادات',
    apiConnected: 'الخادم متصل',
    apiDisconnected: 'الخادم غير متصل',
    apiChecking: 'جارٍ الاتصال...',
    zeroCostTag: 'باقة مجانية 100%',

    // Knowledge Journey
    journeyTitle: 'مسار التعلم والاستيعاب التقني',
    stageUnderstand: 'استيعاب (Understand)',
    stageUnderstandDesc: 'تحليل معمق للمفاهيم التقنية واستخلاص الملخصات المعمارية الدقيقة',
    stageListen: 'استماع (Listen)',
    stageListenDesc: 'توليد صوتي محلي للملخصات التقنية بدون خدمات سحابية مدفوعة',
    stagePractice: 'ممارسة (Practice)',
    stagePracticeDesc: 'بطاقات تقنية تفاعلية وتمارين تثبيت المفاهيم الهندسية',
    stageMaster: 'إتقان (Master)',
    stageMasterDesc: 'محاورة تفاعلية عبر تقنية RAG واستخراج الشيفرات البرمجية',
    comingSoon: 'قريباً',
    currentStage: 'المرحلة النشطة',

    // Dashboard
    dashboardTitle: 'نظرة عامة على النظام',
    dashboardSubtitle: 'مؤشرات معالجة المستندات والنشاط التقني المباشر من قاعدة البيانات',
    statTotalDocs: 'إجمالي المستندات',
    statTotalSummaries: 'الملخصات المولدة',
    statProcessedDocs: 'مستندات جاهزة للتحليل',
    statFailedDocs: 'مستندات تتطلب مراجعة',
    quickUploadTitle: 'رفع مستند سريع',
    quickUploadDesc: 'أسقط ملف PDF أو Markdown أو مواصفات تقنية لبدء المعالجة الفورية',
    quickUploadAction: 'رفع مستند الآن',
    recentDocsTitle: 'أحدث المستندات المرفوعة',
    recentDocsViewAll: 'عرض الكل في المكتبة',
    noDocsYet: 'لم يتم رفع أي مستندات حتى الآن',
    noDocsYetDesc: 'ابدأ برفع ورقة بحثية أو مواصفة معمارية للبدء في استخلاص الملخصات.',
    recentActivityTitle: 'أحدث العمليات في النظام',
    activityDocUploaded: 'تم استلام المستند والتحقق من صحته',
    activityDocProcessed: 'تم استخراج النص وتجهيزه للتوليد الذكي',

    // Document Library
    libraryTitle: 'مكتبة المستندات',
    librarySubtitle: 'إدارة المواصفات التقنية والأوراق البحثية والأدلة المعمارية',
    uploadButton: 'رفع مستند جديد',
    searchPlaceholder: 'البحث عن المستند بالاسم...',
    filterAll: 'جميع الحالات',
    filterProcessed: 'مُعالج بنجاح',
    filterPending: 'قيد المعالجة',
    filterFailed: 'فشل المعالجة',
    filterUnsupported: 'غير مدعوم (ممسوح ضوئياً)',
    thFilename: 'اسم المستند',
    thType: 'النوع',
    thSize: 'الحجم',
    thWords: 'الكلمات',
    thPages: 'الصفحات',
    thStatus: 'الحالة',
    thDate: 'تاريخ الرفع',
    thActions: 'الإجراءات',
    actionOpenWorkspace: 'فتح في مساحة العمل',
    actionDelete: 'حذف',
    paginationPage: 'صفحة',
    paginationOf: 'من أصل',
    paginationPrev: 'السابق',
    paginationNext: 'التالي',
    dropzoneTitle: 'اسحب وأفلت مستندك التقني هنا',
    dropzoneSubtitle: 'أو انقر لاختيار ملف من جهازك',
    dropzoneActive: 'أفلت الملف الآن لبدء التحقق...',
    supportedFormatsNotice: 'يدعم صيغ PDF و TXT و Markdown (الحد الأقصى 15 ميجابايت). حفظ محلي آمن.',
    uploading: 'جارٍ رفع المستند واستخراج النصوص...',
    uploadSuccess: 'تم رفع المستند ومعالجة نصوصه بنجاح!',
    uploadError: 'تعذر رفع المستند. يرجى مراجعة الملف والمحاولة ثانية.',

    // Delete Modal
    deleteModalTitle: 'تأكيد حذف المستند',
    deleteModalWarning: 'هذا الإجراء نهائي ولا يمكن التراجع عنه. سيتم حذف المستند والنصوص المستخرجة وكافة الملخصات المرتبطة به من القرص المحلي.',
    deleteModalPrompt: 'هل أنت متأكد من رغبتك في حذف:',
    deleteModalCancel: 'إلغاء',
    deleteModalConfirm: 'حذف نهائي',
    deleting: 'جارٍ الحذف...',

    // Workspace
    workspaceTitle: 'مساحة العمل والتحليل الذكي',
    workspaceDocInfo: 'بيانات المستند',
    tabSummary: 'الملخص التقني الذكي',
    tabSourceText: 'النص الأصلي المستخرج',
    tabHistory: 'سجل الملخصات السابقة',
    controlsTitle: 'إعدادات التوليد والتلخيص',
    outputLanguageLabel: 'لغة الملخص الناتجة',
    langArabic: 'اللغة العربية الفصحى الحديثة',
    langEnglish: 'اللغة الإنجليزية التقنية (English)',
    detailLevelLabel: 'مستوى التفصيل',
    detailShort: 'موجز (Short)',
    detailShortDesc: '3-5 مفاهيم محورية وخلاصات تنفيذية سريعة',
    detailStandard: 'شامل (Standard)',
    detailStandardDesc: 'تحليل معمق متوازن يجمع المفاهيم والنتائج',
    detailDetailed: 'مفصل (Detailed)',
    detailDetailedDesc: 'تشريح دقيق للعلاقات المعمارية والقيود التقنية',
    generateSummaryBtn: 'توليد الملخص الذكي',
    generatingSummary: 'جارٍ التوليد عبر Gemini (باقة مجانية)...',
    statusCached: 'مسترجع فورياً من الذاكرة المؤقتة المحلية SQLite (0 استهلاك للذكاء الاصطناعي)',
    statusFresh: 'مُولد حديثاً عبر نموذج Gemini 3.8 Flash المجاني',
    statusPending: 'في قائمة الانتظار',
    statusProcessing: 'جارٍ التحليل والتوليد...',
    statusCompleted: 'اكتمل بنجاح',
    statusFailed: 'تعذر التوليد',

    // Summary Viewer Sections
    sectionExecutive: 'الملخص التنفيذي المعماري',
    sectionConcepts: 'المفاهيم والاصطلاحات التقنية المحورية',
    sectionFindings: 'أهم النتائج والاستنتاجات الهندسية',
    sectionArchitecture: 'المعمارية التقنية وتصميم النظام',
    sectionApplications: 'التطبيقات العملية وحالات الاستخدام',
    sectionLimitations: 'القيود المعمارية والمفاضلات التقنية (Trade-offs)',
    sectionTakeaways: 'الخلاصات المعمارية القابلة للتطبيق',
    sectionSources: 'المراجع والاقتباسات الدقيقة من الأصل',
    sourcePagesLabel: 'الصفحات المستشهد بها من المستند',
    sourceChunksLabel: 'المقاطع المستشهد بها',
    sourceDisclaimer: 'إخلاء مسؤولية الاقتباس',
    noSourcePagesAvailable: 'أرقام الصفحات غير متوفرة (مستند نصي عادي أو Markdown)',
    relatedConceptsLabel: 'عناصر ومفاهيم معمارية مرتبطة',
    noSummaryYet: 'لم يتم توليد ملخص لهذا المستند بعد',
    noSummaryYetDesc: 'حدد لغة الإخراج ومستوى التفصيل أعلاه، ثم انقر على "توليد الملخص الذكي".',
    viewingSummaryFrom: 'عرض ملخص تم توليده بتاريخ',
    modelBadgePrefix: 'النموذج',

    // Audio Studio
    tabAudio: 'استوديو الصوت والبودكاست',
    audioModeLabel: 'صيغة الإنتاج الصوتي',
    audioModeNarration: 'شرح صوتي تقني',
    audioModeNarrationDesc: 'شرح تقني مركز بصوت منفرد مستند لأهم المفاهيم المعمارية.',
    audioModePodcast: 'بودكاست تعليمي حواري',
    audioModePodcastDesc: 'حوار تفاعلي معمق بين مقدم ومحاور مع فواصل طبيعية 450ms بين الأدوار.',
    audioVoiceLabel: 'الصوت والمتحدث',
    voiceMale: 'صوت ذكوري',
    voiceFemale: 'صوت أنثوي',
    voiceHost: 'المقدم',
    voiceCohost: 'المحاور',
    generateAudioBtn: 'توليد الصوت (مجاناً $0)',
    generatingAudio: 'جارٍ إنتاج الصوت والتركيب...',
    audioPlayerTitle: 'مشغل الصوت',
    audioSpeed: 'السرعة',
    audioDownloadMp3: 'تحميل ملف MP3',
    audioTranscriptTitle: 'نص الحوار والتفريغ الصوتي',
    audioHistoryTitle: 'التسجيلات الصوتية السابقة',
    noAudioYet: 'لا توجد تسجيلات صوتية بعد',
    noAudioYetDesc: 'ابدأ بإنتاج شرح صوتي أو حلقة بودكاست تعليمية مستندة إلى محتوى هذا المستند.',
    conversationalPauseNotice: 'مدعوم بفواصل حوارية طبيعية 450ms بين المتحدثين',
    audioGeneratingCardTitle: 'جارٍ معالجة وإنتاج الحلقة الصوتية...',
    audioGeneratingCardDesc: 'توليد أصوات المتحدثين الطبيعية وإدراج الفواصل الزمنية قيد التنفيذ.',
    audioFailedCardTitle: 'تعذر إنتاج المقطع الصوتي',
    audioFailedCardDesc: 'حدث خطأ أثناء معالجة الصوت. يمكنك إعادة المحاولة مجاناً.',

    // Learning Studio
    tabLearning: 'استوديو التعلم',
    learningStudioTitle: 'مسار التعلم التقني التفاعلي',
    learningStudioDesc: 'تحويل المستندات التقنية إلى مسارات تعليمية منهجية ومستندة لمصادر دقيقة مع شروحات وأمثلة عملية.',
    learningDifficultyLabel: 'المستوى المستهدف والصعوبة',
    learningLanguageLabel: 'لغة المسار التعليمي',
    difficultyBeginner: 'مبتدئ',
    difficultyBeginnerDesc: 'المفاهيم الأساسية، شروحات مبسطة، والمصطلحات الجوهرية.',
    difficultyIntermediate: 'متوسط',
    difficultyIntermediateDesc: 'التعمق في المعمارية، أنماط التنفيذ، والمفاضلات العملية.',
    difficultyAdvanced: 'متقدم',
    difficultyAdvancedDesc: 'الأسرار الهندسية المتقدمة، حالات الحافة، الأداء، ونقاط الإخفاق.',
    generateLearningPathBtn: 'توليد مسار التعلم (مجاناً $0)',
    generatingLearningPath: 'جارٍ بناء المنهج التعليمي...',
    learningPathHistoryTitle: 'المسارات التعليمية السابقة',
    noLearningPathsYet: 'لا توجد مسارات تعلم بعد',
    noLearningPathsYetDesc: 'حدد مستوى الصعوبة واللغة أعلاه لتوليد مسار تعليمي موثق من هذا المستند.',
    modulesLabel: 'الوحدات التعليمية',
    lessonsLabel: 'الدروس',
    estimatedMinutesLabel: 'دقيقة',
    prerequisitesLabel: 'المتطلبات السابقة',
    learningObjectivesLabel: 'الأهداف التعليمية',
    keyConceptsLabel: 'المفاهيم التقنية الرئيسية',
    exampleSnippetLabel: 'مثال تطبيقي أو شيفرة برمجية',
    sourceReferencesLabel: 'التوثيق والاقتباس من المستند الأصلي',
    learningGeneratingCardTitle: 'جارٍ بناء مسار التعلم الموثق...',
    learningGeneratingCardDesc: 'يقوم الذكاء الاصطناعي بتحليل مقاطع المستند وتوليد منهج تعليمي منظم. يستغرق ذلك قرابة 15-30 ثانية.',
    learningFailedCardTitle: 'تعذر توليد مسار التعلم',
    learningFailedCardDesc: 'حدث خطأ أثناء بناء المنهج. يمكنك إعادة المحاولة مجاناً.',
    viewPathDetails: 'هيكل المنهج',
    retryGeneration: 'إعادة المحاولة',
    sourceReferencePill: 'مرجع أصلي',

    // Phase 5B: Interactive Quizzes & Assessments
    takeLessonQuizBtn: 'اختبار قصير: قياس الفهم',
    takeModuleAssessmentBtn: 'تقييم شامل للوحدة',
    takeFinalAssessmentBtn: 'الاختبار النهائي الشامل',
    assessmentModalTitle: 'التقييم التفاعلي الموثق',
    questionStepLabel: 'السؤال',
    submitAnswerBtn: 'تثبيت الإجابة',
    submittingAnswer: 'جارٍ الحفظ...',
    submitAssessmentBtn: 'إنهاء وتصحيح التقييم محلياً',
    submittingAssessment: 'جارٍ التصحيح الفوري...',
    assessmentResultsTitle: 'نتائج التقييم والمراجعة المنهجية',
    assessmentScoreLabel: 'الدرجة النهائية',
    assessmentPassedBadge: 'ناجح',
    assessmentFailedBadge: 'بحاجة للمراجعة',
    retakeAssessmentBtn: 'إعادة الاختبار',
    yourAnswerLabel: 'إجابتك',
    correctAnswerLabel: 'الإجابة الصحيحة',
    pedagogicalExplanationLabel: 'الشرح المعرفي والتعليل',
    groundedSourceCitationLabel: 'التوثيق من المستند الأصلي',
    assessmentGeneratingTitle: 'جارٍ توليد أسئلة التقييم الموثقة...',
    assessmentGeneratingDesc: 'يقوم النظام بصياغة أسئلة اختيار من متعدد مستندة لنصوص ومقاطع المستند...',
    nextQuestionBtn: 'السؤال التالي',
    prevQuestionBtn: 'السؤال السابق',

    // Phase 5C: Learning Progress & Dashboard
    tabCurriculum: 'هيكل المنهج والدروس',
    tabProgressDashboard: 'لوحة قياس التعلم والإتقان',
    progressOverviewTitle: 'نظرة عامة على التقدم في المنهج',
    completionRateLabel: 'نسبة الإنجاز الكلية',
    completedLessonsLabel: 'الدروس المكتملة',
    remainingLessonsLabel: 'الدروس المتبقية',
    assessmentPassRateLabel: 'نسبة اجتياز الاختبارات',
    averageQuizScoreLabel: 'متوسط الدرجات',
    resumeLearningBtn: 'متابعة التعلم',
    markLessonCompletedBtn: 'تحديد الدرس كمكتمل',
    lessonCompletedBadge: 'مكتمل',
    lessonInProgressBadge: 'قيد التعلم',
    moduleProgressLabel: 'تقدم الوحدة',
    knowledgeMasteryTitle: 'مستوى التمكن المعرفي والأداء',
    strongConceptsTitle: 'المفاهيم المتقنة بثقة',
    conceptsNeedingReviewTitle: 'مفاهيم بحاجة للمراجعة والتركيز',
    frequentlyMissedQuestionsTitle: 'الأسئلة الأكثر خطأً',
    noMissedQuestionsYet: 'لا توجد أخطاء متكررة مسجلة، أداء ممتاز!',
    noStrongConceptsYet: 'اجتز اختبارات الدروس بنسبة 70% أو أكثر لإثبات إتقان المفاهيم.',
    noConceptsNeedingReviewYet: 'لا توجد مفاهيم متعثرة حالياً بحاجة للمراجعة.',
    smartRecommendationsTitle: 'التوجيهات والتوصيات التعليمية الذكية',
    noRecommendationsYet: 'ابدأ بقراءة الدروس للحصول على توجيهات تعليمية مخصصة.',
    recentAssessmentsHistoryTitle: 'سجل محاولات التقييم',
    noAssessmentsAttemptedYet: 'لم يتم خوض أي تقييم بعد.',
    evidenceLabel: 'الدليل القياسي',
    failureRateLabel: 'نسبة الخطأ',

    // Settings
    settingsTitle: 'إعدادات المنصة',
    settingsSubtitle: 'تخصيص لغة الواجهة، المظهر العام، وتفضيلات التحليل المحلي',
    sectionPreferences: 'تفضيلات المستخدم',
    uiLanguageLabel: 'لغة الواجهة الرئيسية',
    themeLabel: 'المظهر اللوني',
    themeLight: 'الوضع الفاتح (Light)',
    themeDark: 'الوضع الداكن (Dark)',
    themeSystem: 'حسب النظام',
    defaultSummaryLangLabel: 'لغة التلخيص الافتراضية',
    defaultDetailLevelLabel: 'مستوى التفصيل الافتراضي',
    sectionSystemHealth: 'حالة اتصال الخادم وتشخيص النظام',
    backendStatusLabel: 'حالة خادم FastAPI',
    backendVersionLabel: 'إصدار واجهة التطبيق (API)',
    backendEnvLabel: 'بيئة التشغيل',
    testConnectionBtn: 'فحص اتصال الخادم',
    testingConnection: 'جارٍ الفحص...',
    zeroCostGuaranteeTitle: 'ضمان التكلفة الصفرية (Zero-Cost Architecture)',
    zeroCostGuaranteeDesc: 'يعمل TechSift AI محلياً بالكامل بالاعتماد على SQLite (aiosqlite) والحصص المجانية المعتمدة لنموذج Google Gemini 3.8 Flash. لا توجد أي خدمات سحابية مدفوعة ولا يتطلب بطاقة بنكية.',
    savePreferencesSuccess: 'تم حفظ التفضيلات محلياً بنجاح!',

    // Common & Errors
    loading: 'جارٍ تحميل البيانات...',
    retry: 'إعادة المحاولة',
    close: 'إغلاق',
    errorTitle: 'خطأ في العملية',
    networkErrorDesc: 'تعذر الاتصال بخادم FastAPI المحلي. تأكد من أن الخادم يعمل على العنوان http://127.0.0.1:8000.',
    fileTooLargeError: 'حجم الملف يتجاوز الحد الأقصى المسموح به (15 ميجابايت).',
    invalidFileFormatError: 'صيغة الملف غير مدعومة. يرجى رفع ملف بصيغة PDF أو TXT أو Markdown.',
    scannedPdfNotice: 'تنبيه: ملفات PDF الممسوحة ضوئياً كصور لا تحتوي على نصوص قابلة للاستخراج.',
  },
};
