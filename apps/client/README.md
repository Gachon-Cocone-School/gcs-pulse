# Modern LMS Design System

이 프로젝트는 **Modern LMS (Learning Management System) Design System**입니다. **Next.js (App Router)**, React, Tailwind CSS, 그리고 **shadcn/ui**를 사용하여 구축되었으며, 현대적이고 접근성 높은 UI 컴포넌트들을 제공합니다.

## 🚀 주요 특징

- **최신 프레임워크**: Next.js 14+ App Router를 사용하여 서버 컴포넌트, 최적화된 라우팅 등 최신 기능을 활용합니다.
- **모던 UI 컴포넌트**: **shadcn/ui**를 기반으로 하여 아름답고 재사용 가능한 컴포넌트를 제공합니다.
- **스타일링**: Tailwind CSS를 사용하여 유연하고 효율적인 스타일링이 가능합니다.
- **접근성(Accessibility)**: Radix UI Primitives를 사용하여 웹 접근성을 준수하는 컴포넌트를 구축했습니다.
- **유틸리티**: `clsx`, `tailwind-merge` 등을 활용하여 조건부 스타일링을 쉽게 처리합니다.

## 🛠 기술 스택 (Tech Stack)

이 프로젝트는 다음의 핵심 기술들을 사용합니다:

### Core FrameWork
- **[Next.js](https://nextjs.org/)**: React 애플리케이션을 위한 강력한 풀스택 프레임워크 (App Router 사용)
- **[React](https://react.dev/)**: 사용자 인터페이스를 만들기 위한 JavaScript 라이브러리
- **[TypeScript](https://www.typescriptlang.org/)**: JavaScript에 타입을 더한 상위 집합 언어

### Styling & Components
- **[shadcn/ui](https://ui.shadcn.com/)**: Radix UI와 Tailwind CSS를 기반으로 한, 복사/붙여넣기 가능한 아름다운 컴포넌트 라이브러리
- **[Tailwind CSS](https://tailwindcss.com/)**: 유틸리티 우선(Utility-first)의 CSS 프레임워크
- **[Radix UI](https://www.radix-ui.com/)**: 접근성이 보장된 Headless UI 컴포넌트 라이브러리
- **[Lucide React](https://lucide.dev/)**: 아름답고 일관된 아이콘 라이브러리
- **[Recharts](https://recharts.org/)**: React를 위한 구성 가능한 차트 라이브러리

### State & Forms
- **[React Hook Form](https://react-hook-form.com/)**: 성능이 뛰어나고 유연한 폼 유효성 검사 라이브러리

## 📂 프로젝트 구조 (Project Structure)

```
/
├── public/              # 정적 파일 (이미지, 폰트 등)
├── src/
│   ├── app/             # Next.js App Router 디렉토리
│   │   ├── layout.tsx   # 최상위 레이아웃
│   │   ├── page.tsx     # 메인 페이지
│   │   └── globals.css  # 전역 스타일
│   ├── assets/          # 이미지 및 미디어 자산
│   ├── components/      # 재사용 가능한 UI 컴포넌트 (Button, Input 등)
│   ├── guidelines/      # 디자인 가이드라인 문서
│   └── styles/          # 추가 스타일 정의
├── package.json         # 프로젝트 의존성 및 스크립트
├── next.config.mjs      # Next.js 설정
└── README.md            # 프로젝트 설명 문서
```

## 🏁 시작하기 (Getting Started)

프로젝트를 로컬 환경에서 실행하려면 다음 단계들을 따르세요.

### 1. 사전 요구사항 (Prerequisites)
- [Node.js](https://nodejs.org/) (버전 18.17 이상 권장)
- npm 또는 yarn 패키지 매니저

### 2. 설치 (Installation)
터미널에서 프로젝트 디렉토리로 이동한 후 의존성을 설치합니다.

```bash
npm install
```

### 3. 개발 서버 실행 (Run Development Server)
설치가 완료되면 개발 서버를 시작합니다.

```bash
npm run dev
```
브라우저에서 `http://localhost:3000`을 열어 프로젝트를 확인하세요.

### 4. 빌드 (Build)
배포를 위해 프로덕션 빌드를 생성하려면 다음 명령어를 실행합니다.

```bash
npm run build
```
빌드된 파일은 `.next/` 디렉토리에 생성됩니다.

---

*이 문서는 프로젝트의 현재 상태를 기반으로 작성되었습니다.*